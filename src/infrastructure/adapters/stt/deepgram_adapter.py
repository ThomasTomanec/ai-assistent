"""Deepgram cloud STT adapter - WAV wrapper"""

import asyncio
import io
import wave
import numpy as np
import structlog
import httpx
from src.core.ports.i_stt_engine import ISTTEngine

logger = structlog.get_logger()

def to_wav_bytes(audio_int16: np.ndarray, sample_rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    return buf.getvalue()

class DeepgramAdapter(ISTTEngine):
    """Cloud STT using Deepgram REST API with WAV audio"""

    def __init__(self, api_key: str, language: str = "cs"):
        self.api_key = api_key
        self.language = language
        self.base_url = "https://api.deepgram.com/v1/listen"
        logger.info("deepgram_adapter_initialized", language=language)

    async def transcribe(self, audio_data: np.ndarray) -> str:
        try:
            if audio_data.dtype != np.int16:
                audio_int16 = (np.clip(audio_data, -1.0, 1.0) * 32768).astype(np.int16) if audio_data.dtype == np.float32 else audio_data.astype(np.int16)
            else:
                audio_int16 = audio_data

            audio_bytes = to_wav_bytes(audio_int16, 16000)

            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "audio/wav"
            }

            params = {
                "model": "nova-2",
                "language": self.language,
                "smart_format": "true",
                "punctuate": "true"
                # encoding, sample_rate, channels vynechány, vezme se z WAV
            }

            logger.info("deepgram_transcribing", params=params)
            async with httpx.AsyncClient(timeout=httpx.Timeout(40.0)) as client:
                resp = await client.post(
                    self.base_url,
                    headers=headers,
                    params=params,
                    content=audio_bytes
                )

            if resp.status_code != 200:
                try:
                    err_json = resp.json()
                except Exception:
                    err_json = {"text": resp.text}
                logger.error("deepgram_http_error", status=resp.status_code, detail=err_json)
                return ""

            result = resp.json()
            alt = result["results"]["channels"][0]["alternatives"][0]
            text = (alt.get("transcript") or "").strip()
            confidence = alt.get("confidence", None)
            logger.info("deepgram_complete", text=text[:100], confidence=confidence)
            return text

        except Exception as e:
            msg = ""
            if hasattr(e, "response") and e.response:
                try:
                    msg = e.response.text
                except Exception:
                    msg = str(e)
            logger.error("deepgram_error", error=str(e), server_msg=msg, exc_info=True)
            return ""
