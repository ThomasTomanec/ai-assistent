"""Audio input port (interface)"""

from abc import ABC, abstractmethod
from typing import Optional
import numpy as np

class IAudioInput(ABC):
    """Abstract audio input interface"""
    
    @abstractmethod
    def start_stream(self):
        """Start continuous audio stream"""
        pass
    
    @abstractmethod
    async def read_chunk(self, stream) -> np.ndarray:
        """Read single audio chunk from stream"""
        pass
    
    @abstractmethod
    async def record_command(self, duration: float) -> np.ndarray:
        """Record audio for specified duration"""
        pass
    
    @abstractmethod
    def stop_stream(self):
        """Stop and close audio stream"""
        pass
