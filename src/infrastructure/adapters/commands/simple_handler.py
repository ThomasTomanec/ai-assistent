"""Simple command handler"""

import structlog
from src.core.ports.i_command_handler import ICommandHandler

logger = structlog.get_logger()

class SimpleCommandHandler(ICommandHandler):
    """Simple keyword-based command handler"""
    
    def __init__(self):
        logger.info("simple_command_handler_initialized")
    
    def process(self, text: str) -> str:
        """
        Process command using simple keyword matching
        
        Args:
            text: Command text from user
            
        Returns:
            Response text
        """
        text_lower = text.lower().strip()
        logger.info("processing_command", text=text)
        
        # Weather
        if any(word in text_lower for word in ['počasí', 'weather', 'teplota']):
            return "Venku je asi 15°C a polojasno. (simulace - později přidám skutečná data)"
        
        # Time
        elif any(word in text_lower for word in ['čas', 'time', 'kolik']):
            from datetime import datetime
            now = datetime.now()
            return f"Je {now.hour}:{now.minute:02d}."
        
        # Help
        elif any(word in text_lower for word in ['pomoc', 'help', 'nápověda']):
            return (
                "Umím ti říct počasí, čas, nebo můžeš říct 'ahoj'. "
                "Zatím jsem v testovací verzi."
            )
        
        # Greeting
        elif any(word in text_lower for word in ['ahoj', 'hello', 'hey', 'nazdar']):
            return "Ahoj! Jak ti mohu pomoci?"
        
        # Default
        else:
            return "Rozumím. Zatím to neumím. Zkus říct 'pomoc' pro seznam příkazů."
