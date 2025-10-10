"""Wake word detector port"""

from abc import ABC, abstractmethod
import numpy as np

class IWakeWordDetector(ABC):
    """Abstract wake word detector interface"""
    
    @abstractmethod
    def detect(self, audio_chunk: np.ndarray) -> bool:
        """
        Detect wake word in audio chunk
        
        Args:
            audio_chunk: Audio data as numpy array
            
        Returns:
            True if wake word detected, False otherwise
        """
        pass
    
    @abstractmethod
    def reset(self):
        """Reset detector internal state"""
        pass
