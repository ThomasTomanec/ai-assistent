"""Hybrid STT with Groq primary, Whisper fallback"""

import structlog
from src.core.ports.i_stt_engine import ISTTEngine
from src.infrastructure.adapters.stt.groq_whisper_adapter import GroqWhisperAdapter
from src.infrastructure.adapters.stt.whisper_adapter import WhisperAdapter

logger = structlog.get_logger()

class HybridSTTAdapter(ISTTEngine):
    """
    Hybrid STT: Groq Whisper primary (rychlý, zdarma), lokální Whisper fallback
    """
    
    def __init__(self, groq_api_key: str = "", whisper_model: str = "small", language: str = "cs"):
        self.groq_enabled = bool(groq_api_key)
        
        if self.groq_enabled:
            self.primary = GroqWhisperAdapter(api_key=groq_api_key, language=language)
            logger.info("hybrid_stt_groq_enabled")
        
        # Lokální Whisper jako fallback
        self.fallback = WhisperAdapter(model_size=whisper_model, language=language)
        
        logger.info("hybrid_stt_initialized", primary="groq" if self.groq_enabled else "local", fallback="whisper")
    
    async def transcribe(self, audio_data: bytes) -> str:
        # Zkus primární (Groq)
        if self.groq_enabled:
            try:
                logger.info("trying_groq_stt")
                text = await self.primary.transcribe(audio_data)
                if text:
                    logger.info("groq_stt_success", length=len(text))
                    return text
            except Exception as e:
                logger.warning("groq_stt_failed", error=str(e))
        
        # Fallback na lokální Whisper
        logger.info("using_local_whisper_fallback")
        return await self.fallback.transcribe(audio_data)
