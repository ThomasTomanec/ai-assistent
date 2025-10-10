"""Voice Activity Detection"""
import webrtcvad
import numpy as np


class VAD:
    """Voice Activity Detector using WebRTC VAD"""
    
    def __init__(self, mode: int = 3, sample_rate: int = 16000):
        self.vad = webrtcvad.Vad(mode)
        self.sample_rate = sample_rate
    
    def is_speech(self, audio: np.ndarray) -> bool:
        """Check if audio contains speech"""
        audio_bytes = (audio * 32768).astype(np.int16).tobytes()
        return self.vad.is_speech(audio_bytes, self.sample_rate)
