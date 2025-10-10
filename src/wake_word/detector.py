"""Wake word detection using openWakeWord"""
import asyncio
import numpy as np
import structlog
from abc import ABC, abstractmethod

logger = structlog.get_logger()


class WakeWordDetector(ABC):
    """Abstract wake word detector"""
    
    @abstractmethod
    async def detect(self, audio: np.ndarray) -> bool:
        """Detect wake word in audio chunk"""
        pass


class OpenWakeWordDetector(WakeWordDetector):
    """OpenWakeWord detector (disabled for testing)"""
    
    def __init__(self, keywords: list = None, threshold: float = 0.5):
        self.keywords = keywords or ['alexa']
        self.threshold = threshold
        self.model = None
        
        logger.info("openwakeword_detector_initialized_TESTING_MODE", 
                   keywords=self.keywords, threshold=threshold)
    
    async def initialize(self):
        """Initialize - SKIPPED in testing mode"""
        logger.info("skipping_wake_word_initialization_for_testing")
        pass
    
    async def detect(self, audio: np.ndarray) -> bool:
        """Detect wake word - NOT USED in testing mode"""
        return False