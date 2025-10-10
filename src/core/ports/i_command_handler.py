"""Command handler port"""

from abc import ABC, abstractmethod

class ICommandHandler(ABC):
    """Abstract command handler interface"""
    
    @abstractmethod
    def process(self, text: str) -> str:
        """
        Process command text and return response
        
        Args:
            text: Command text from user
            
        Returns:
            Response text
        """
        pass
