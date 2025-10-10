"""Audio capture from microphone"""
import asyncio
import numpy as np
import sounddevice as sd
from typing import AsyncIterator
import structlog
from src.core.exceptions import AudioCaptureError

logger = structlog.get_logger()


class AudioCapture:
    """Handles audio input from microphone"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1, 
                 chunk_size: int = 1024, device: int = None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device = device
        
        logger.info("audio_capture_initialized", 
                   sample_rate=sample_rate, channels=channels)
    
    async def stream(self) -> AsyncIterator[np.ndarray]:
        """Stream audio from microphone"""
        try:
            loop = asyncio.get_event_loop()
            queue = asyncio.Queue()
            
            def callback(indata, frames, time, status):
                if status:
                    logger.warning("audio_stream_status", status=status)
                loop.call_soon_threadsafe(queue.put_nowait, indata.copy())
            
            stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=callback,
                blocksize=self.chunk_size,
                device=self.device
            )
            
            with stream:
                logger.info("audio_stream_started")
                while True:
                    chunk = await queue.get()
                    yield chunk[:, 0] if self.channels == 1 else chunk
                    
        except Exception as e:
            logger.error("audio_capture_error", error=str(e))
            raise AudioCaptureError(f"Failed to capture audio: {e}")
    
    async def capture_until_silence(self, silence_threshold: float = 2.0) -> np.ndarray:
        """Capture audio until silence detected"""
        chunks = []
        timeout = 5.0
        
        try:
            async with asyncio.timeout(timeout):
                async for chunk in self.stream():
                    chunks.append(chunk)
                    if len(chunks) > int(silence_threshold * self.sample_rate / self.chunk_size):
                        break
        except asyncio.TimeoutError:
            logger.warning("capture_timeout")
        
        return np.concatenate(chunks) if chunks else np.array([])
