"""Voice Activity Detection helper"""

import numpy as np
import webrtcvad
import structlog

logger = structlog.get_logger()

class VADHelper:
    """Voice Activity Detection using WebRTC VAD"""
    
    def __init__(self, sample_rate: int = 16000, aggressiveness: int = 2):
        """
        Initialize VAD
        
        Args:
            sample_rate: Audio sample rate (must be 8000, 16000, 32000, or 48000)
            aggressiveness: VAD aggressiveness (0-3, higher = more aggressive)
        """
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate
        logger.info("vad_initialized", sample_rate=sample_rate, aggressiveness=aggressiveness)
    
    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        Check if audio chunk contains speech
        
        Args:
            audio_chunk: Audio data (int16, 1280 samples for 16kHz)
            
        Returns:
            True if speech detected, False otherwise
        """
        try:
            # Ensure int16
            if audio_chunk.dtype != np.int16:
                audio_chunk = audio_chunk.astype(np.int16)
            
            # Flatten
            if len(audio_chunk.shape) > 1:
                audio_chunk = audio_chunk.flatten()
            
            # Convert to bytes
            audio_bytes = audio_chunk.tobytes()
            
            # Check speech (requires exact frame sizes: 10, 20, or 30 ms)
            # 1280 samples @ 16kHz = 80ms, so we check in 320-sample chunks (20ms)
            frame_size = 320  # 20ms at 16kHz
            speech_frames = 0
            total_frames = 0
            
            for i in range(0, len(audio_chunk) - frame_size, frame_size):
                frame = audio_chunk[i:i+frame_size].tobytes()
                if self.vad.is_speech(frame, self.sample_rate):
                    speech_frames += 1
                total_frames += 1
            
            # Speech if >50% of frames contain speech
            speech_ratio = speech_frames / total_frames if total_frames > 0 else 0
            return speech_ratio > 0.5
            
        except Exception as e:
            logger.error("vad_error", error=str(e))
            return False
