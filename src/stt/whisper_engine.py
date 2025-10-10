"""Whisper STT engine (placeholder - install mlx-whisper)"""
import asyncio
import numpy as np
import structlog
from src.stt.engine import STTEngine
from src.core.exceptions import STTError

logger = structlog.get_logger()


class WhisperSTT(STTEngine):
    """Whisper STT - TODO: Install mlx-whisper"""
    
    def __init__(self, model_size: str = "small", language: str = "cs"):
        self.model_size = model_size
        self.language = language
        self.model = None
        
        logger.info("whisper_stt_initialized", 
                   model_size=model_size, language=language)
    
    async def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio - PLACEHOLDER"""
        try:
            if self.model is None:
                await self._load_model()
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._transcribe_sync, audio)
            
            logger.info("transcription_completed", text=result)
            return result
            
        except Exception as e:
            logger.error("transcription_error", error=str(e))
            raise STTError(f"Transcription failed: {e}")
    
    async def _load_model(self):
        """Load Whisper model"""
        logger.info("loading_whisper_model")
        # TODO: Uncomment when mlx-whisper installed
        # import mlx_whisper
        # self.model = mlx_whisper.load_model(f"mlx-community/whisper-{self.model_size}-mlx")
        logger.warning("whisper_model_not_loaded", 
                      message="Install: pip install mlx-whisper")
    
    def _transcribe_sync(self, audio: np.ndarray) -> str:
        """Synchronous transcription"""
        # TODO: Uncomment when model loaded
        # result = self.model.transcribe(audio, language=self.language)
        # return result['text'].strip()
        
        # Placeholder
        return "test transcription - install mlx-whisper"
