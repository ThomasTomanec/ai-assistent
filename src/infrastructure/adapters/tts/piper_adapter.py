"""Piper TTS adapter"""

import structlog

logger = structlog.get_logger()

class PiperAdapter:
    """Text-to-speech using Piper (placeholder for now)"""
    
    def __init__(self, voice: str = "en_US-lessac-medium", rate: float = 1.0):
        """
        Initialize Piper TTS
        
        Args:
            voice: Voice model name
            rate: Speech rate multiplier
        """
        self.voice = voice
        self.rate = rate
        logger.info("piper_tts_initialized", voice=voice, rate=rate)
    
    async def speak(self, text: str):
        """
        Speak text (not yet implemented)
        
        Args:
            text: Text to speak
        """
        logger.info("tts_speak_called", text=text)
        # TODO: Implement actual TTS when needed
        pass
