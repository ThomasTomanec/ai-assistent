"""Audio playback"""
import asyncio
import numpy as np
import sounddevice as sd
import structlog

logger = structlog.get_logger()


class AudioPlayer:
    """Handles audio output"""
    
    def __init__(self, sample_rate: int = 22050, device: int = None):
        self.sample_rate = sample_rate
        self.device = device
    
    async def play(self, audio: np.ndarray):
        """Play audio"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: sd.play(audio, self.sample_rate, device=self.device)
            )
            await loop.run_in_executor(None, sd.wait)
        except Exception as e:
            logger.error("playback_error", error=str(e))
