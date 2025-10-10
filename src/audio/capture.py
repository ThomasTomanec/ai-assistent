"""Audio capture module"""
import asyncio
import numpy as np
import sounddevice as sd
import structlog
from typing import Optional

logger = structlog.get_logger()

class AudioCapture:
    """Handles audio input from microphone"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1, 
                 chunk_size: int = 1280, device: Optional[int] = None,
                 gain: float = 1.0):
        # Force chunk_size to 1280 for OpenWakeWord compatibility
        if chunk_size != 1280:
            logger.warning("chunk_size_adjusted", old=chunk_size, new=1280)
            chunk_size = 1280
            
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device = device
        self.gain = gain  # Audio gain multiplier
        self.stream = None
        
        logger.info("audio_capture_initialized", 
                   sample_rate=sample_rate, 
                   channels=channels,
                   chunk_size=chunk_size,
                   device=device if device else "default",
                   gain=gain)
    
    def start_stream(self):
        """Start continuous audio stream for wake word detection"""
        try:
            self.stream = sd.InputStream(
                device=self.device,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                dtype='int16'
            )
            self.stream.start()
            logger.info("audio_stream_started")
            return self.stream
        except Exception as e:
            logger.error("failed_to_start_stream", error=str(e))
            raise
    
    async def read_chunk(self, stream) -> np.ndarray:
        """Read one chunk from the audio stream"""
        try:
            # Read in a non-blocking way using asyncio
            loop = asyncio.get_event_loop()
            audio_data, overflowed = await loop.run_in_executor(
                None, stream.read, self.chunk_size
            )
            
            if overflowed:
                logger.warning("audio_buffer_overflow")
            
            # Ensure it's flattened
            audio_data = audio_data.flatten()
            
            # Apply gain
            if self.gain != 1.0:
                audio_data = np.clip(audio_data * self.gain, -32768, 32767).astype(np.int16)
            
            return audio_data
        except Exception as e:
            logger.error("read_chunk_error", error=str(e))
            raise
    
    async def record_command(self, duration: float = 5.0) -> np.ndarray:
        """Record audio after wake word is detected"""
        try:
            logger.info("recording_command", duration=duration)
            
            # Calculate number of frames
            frames = int(duration * self.sample_rate)
            
            # Record audio
            loop = asyncio.get_event_loop()
            audio_data = await loop.run_in_executor(
                None,
                sd.rec,
                frames,
                self.sample_rate,
                self.channels,
                'int16',
                self.device
            )
            
            # Wait for recording to complete
            await loop.run_in_executor(None, sd.wait)
            
            # Apply gain
            audio_data = audio_data.flatten()
            if self.gain != 1.0:
                audio_data = np.clip(audio_data * self.gain, -32768, 32767).astype(np.int16)
            
            logger.info("recording_complete", frames=len(audio_data))
            return audio_data
            
        except Exception as e:
            logger.error("recording_error", error=str(e))
            raise
    
    def stop_stream(self):
        """Stop the audio stream"""
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                logger.info("audio_stream_stopped")
            except Exception as e:
                logger.error("stop_stream_error", error=str(e))
