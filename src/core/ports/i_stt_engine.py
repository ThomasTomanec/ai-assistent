"""Speech-to-text engine port"""

from abc import ABC, abstractmethod
import numpy as np

class ISTTEngine(ABC):
    """Abstract speech-to-text engine interface"""
    
    @abstractmethod
    async def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribe audio to text
        
        Args:
            audio_data: Audio data as numpy array
            
        Returns:
            Transcribed text string
        """
        pass
