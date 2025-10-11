"""
Deepgram cloud STT adapter - WAV wrapper
Vylepšeno: config z UserConfig, retry logic, lepší error handling
"""

import asyncio
import io
import wave
import time
import numpy as np
import structlog
import httpx
from src.core.ports.i_stt_engine import ISTTEngine
from src.core.exceptions import STTError

logger = structlog.get_logger()


def to_wav_bytes(audio_int16: np.ndarray, sample_rate: int = 16000) -> bytes:
    """Convert int16 audio to WAV bytes"""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    return buf.getvalue()


class DeepgramAdapter(ISTTEngine):
    """Cloud STT using Deepgram REST API with WAV audio"""

    def __init__(self, api_key: str, language: str = "cs", user_config=None):
        """
        Args:
            api_key: Deepgram API key
            language: Language code
            user_config: UserConfig instance
        """
        self.api_key = api_key
        self.language = language
        self.base_url = "https://api.deepgram.com/v1/listen"

        # Load config
        if user_config:
            self.model = user_config.get('audio.stt.deepgram_model', 'nova-2')
            self.timeout = user_config.get('audio.stt.deepgram_timeout', 40.0)
            self.max_retries = user_config.get('audio.stt.max_retries', 3)
        else:
            self.model = 'nova-2'
            self.timeout = 40.0
            self.max_retries = 3

        logger.info("deepgram_adapter_initialized",
                   language=language,
                   model=self.model)

    async def _transcribe_with_retry(self, audio_bytes: bytes, params: dict) -> dict:
        """
        Transcribe s retry logikou.

        Args:
            audio_bytes: WAV audio bytes
            params: Query parameters

        Returns:
            Deepgram response JSON
        """
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav"
        }

        last_error = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
                    resp = await client.post(
                        self.base_url,
                        headers=headers,
                        params=params,
                        content=audio_bytes
                    )

                if resp.status_code == 200:
                    return resp.json()
                else:
                    error_msg = f"HTTP {resp.status_code}"
                    try:
                        error_detail = resp.json()
                        error_msg += f": {error_detail}"
                    except:
                        error_msg += f": {resp.text[:200]}"

                    logger.error("deepgram_http_error",
                               status=resp.status_code,
                               detail=error_msg)
                    raise STTError(error_msg)

            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_error = e

                if attempt == self.max_retries - 1:
                    raise

                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(
                    "deepgram_stt_retry",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    wait_seconds=wait_time,
                    error=str(e)
                )
                await asyncio.sleep(wait_time)

        raise last_error

    async def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribe audio using Deepgram.

        Args:
            audio_data: Audio data (int16 or float32)

        Returns:
            Transcribed text
        """
        try:
            # Convert to int16 if needed
            if audio_data.dtype != np.int16:
                if audio_data.dtype == np.float32:
                    audio_int16 = (np.clip(audio_data, -1.0, 1.0) * 32768).astype(np.int16)
                else:
                    audio_int16 = audio_data.astype(np.int16)
            else:
                audio_int16 = audio_data

            # Convert to WAV
            audio_bytes = to_wav_bytes(audio_int16, 16000)

            # Prepare parameters
            params = {
                "model": self.model,
                "language": self.language,
                "smart_format": "true",
                "punctuate": "true"
            }

            logger.info("deepgram_transcribing",
                       params=params,
                       audio_size=len(audio_bytes))

            # Transcribe with retry
            result = await self._transcribe_with_retry(audio_bytes, params)

            # Extract text
            alt = result["results"]["channels"][0]["alternatives"][0]
            text = (alt.get("transcript") or "").strip()
            confidence = alt.get("confidence", None)

            logger.info("deepgram_complete",
                       text=text[:100],
                       confidence=confidence,
                       length=len(text))
            return text

        except Exception as e:
            logger.error("deepgram_transcription_error",
                        error=str(e),
                        error_type=type(e).__name__)
            raise STTError(f"Deepgram transcription failed: {e}") from e
