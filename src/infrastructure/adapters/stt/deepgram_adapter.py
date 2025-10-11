"""Deepgram cloud STT adapter - HTTP fallback"""

import asyncio
import numpy as np
import structlog
import httpx
from src.core.ports.i_stt_engine import ISTTEngine

logger = structlog.get_logger()

class DeepgramAdapter(ISTTEngine):
    """Cloud STT using Deepgram REST API"""

    def __init__(self, api_key: str, language: str = "cs"):
        self.api_key = api_key
        self.language = language
        self.base_url = "https://api.deepgram.com/v1/listen"
        logger.info("deepgram_adapter_initialized", language=language)

    async def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribe audio via Deepgram HTTP API.
        Works with any deepgram-sdk version.
        """
        try:
            # Prepare audio bytes
            if audio_data.dtype == np.int16:
                audio_bytes = audio_data.tobytes()
            else:
                audio_int16 = (audio_data * 32768).astype(np.int16)
                audio_bytes = audio_int16.tobytes()

            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "audio/pcm"
            }

            params = {
                "model": "nova-2",
                "language": self.language,
                "smart_format": "true",
                "punctuate": "true"
            }

            logger.info("deepgram_transcribing")

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.base_url,
                    headers=headers,
                    params=params,
                    content=audio_bytes
                )
                resp.raise_for_status()

            result = resp.json()
            alt = result["results"]["channels"][0]["alternatives"][0]
            text = alt.get("transcript", "").strip()
            confidence = alt.get("confidence", 0)

            logger.info("deepgram_complete", text=text[:100], confidence=confidence)
            return text

        except Exception as e:
            logger.error("deepgram_error", error=str(e), exc_info=True)
            return ""
