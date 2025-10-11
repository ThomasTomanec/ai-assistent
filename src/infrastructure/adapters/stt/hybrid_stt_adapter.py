import asyncio
import numpy as np
import structlog
import httpx
from src.core.ports.i_stt_engine import ISTTEngine
from src.infrastructure.adapters.stt.deepgram_adapter import DeepgramAdapter
from src.infrastructure.adapters.stt.whisper_adapter import WhisperAdapter

logger = structlog.get_logger()

class HybridSTTAdapter(ISTTEngine):
    """
    Hybrid STT adapter:
    - Primary: Deepgram (cloud)
    - Fallback: Whisper (offline)
    """
    def __init__(
        self,
        deepgram_api_key: str,
        whisper_model: str = "small",
        language: str = "cs"
    ):
        self.language = language
        try:
            self.cloud = DeepgramAdapter(deepgram_api_key, language)
            self.has_cloud = True
            logger.info("hybrid_stt_cloud_enabled")
        except Exception as e:
            self.has_cloud = False
            logger.warning("hybrid_stt_cloud_disabled", error=str(e))
        self.local = WhisperAdapter(whisper_model, language)
        logger.info(
            "hybrid_stt_initialized",
            primary="deepgram" if self.has_cloud else "whisper",
            fallback="whisper"
        )

    async def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribe with fallback logic.
        1. Try Deepgram (if available)
        2. If error/empty → use Whisper
        """
        if self.has_cloud:
            try:
                logger.info("trying_cloud_stt")
                text = await self.cloud.transcribe(audio_data)
                if text and len(text.strip()) > 0:
                    logger.info("cloud_stt_success", length=len(text))
                    return text
                else:
                    logger.warning("cloud_returned_empty")
            except httpx.ConnectError:
                logger.warning("cloud_stt_connection_failed_using_local")
            except Exception as e:
                logger.warning("cloud_stt_error_using_local", error=str(e))
        logger.info("using_local_stt")
        text = await self.local.transcribe(audio_data)
        logger.info("local_stt_complete", length=len(text))
        return text

    def is_online(self) -> bool:
        """Check if cloud STT is available"""
        return self.has_cloud
