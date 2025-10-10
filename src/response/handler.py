"""Response handling"""
import asyncio
import numpy as np
import structlog
from pathlib import Path
from src.tts.engine import TTSEngine
from src.audio.player import AudioPlayer

logger = structlog.get_logger()


class ResponseHandler:
    """Handles responses to user"""
    
    def __init__(self, tts_engine: TTSEngine, acknowledge_sound: str = None, 
                 error_sound: str = None):
        self.tts = tts_engine
        self.player = AudioPlayer()
        self.acknowledge_sound = acknowledge_sound
        self.error_sound = error_sound
    
    async def acknowledge(self):
        """Play acknowledgement sound"""
        logger.info("playing_acknowledge_sound")
        print("✨ Acknowledged!")
    
    async def respond(self, text: str):
        """Respond with TTS"""
        logger.info("responding", text=text[:50])
        
        try:
            audio = await self.tts.synthesize(text)
            await self.player.play(audio)
        except Exception as e:
            logger.error("response_error", error=str(e))
            await self.error("synthesis_failed")
    
    async def error(self, error_type: str = "generic"):
        """Handle error"""
        logger.warning("error_response", error_type=error_type)
        
        messages = {
            "generic": "Omlouvám se, něco se pokazilo",
            "no_understand": "Omlouvám se, nerozuměl jsem",
            "no_microphone": "Nemůžu tě slyšet",
            "synthesis_failed": "Mám problém s odpovědí"
        }
        
        message = messages.get(error_type, messages["generic"])
        print(f"❌ {message}")
