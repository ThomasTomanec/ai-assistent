"""Text-to-Speech engine abstraction"""
from abc import ABC, abstractmethod
import numpy as np
from typing import AsyncIterator


class TTSEngine(ABC):
    """Abstract TTS engine"""
    
    @abstractmethod
    async def synthesize(self, text: str) -> np.ndarray:
        """Synthesize text to audio"""
        pass
