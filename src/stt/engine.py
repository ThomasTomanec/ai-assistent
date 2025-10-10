"""Speech-to-Text engine abstraction"""
from abc import ABC, abstractmethod
import numpy as np


class STTEngine(ABC):
    """Abstract STT engine"""
    
    @abstractmethod
    async def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio to text"""
        pass
