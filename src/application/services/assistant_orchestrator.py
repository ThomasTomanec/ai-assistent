"""Assistant orchestration service"""

import asyncio
import structlog
from src.core.ports.i_audio_input import IAudioInput
from src.core.ports.i_wake_word_detector import IWakeWordDetector
from src.core.ports.i_stt_engine import ISTTEngine
from src.core.ports.i_command_handler import ICommandHandler

logger = structlog.get_logger()

class AssistantOrchestrator:
    """
    Orchestrates the voice assistant workflow.
    Pure business logic - no UI concerns.
    """
    
    def __init__(
        self,
        audio_input: IAudioInput,
        wake_word_detector: IWakeWordDetector,
        stt_engine: ISTTEngine,
        command_handler: ICommandHandler
    ):
        self.audio = audio_input
        self.wake_word = wake_word_detector
        self.stt = stt_engine
        self.commands = command_handler
        self.stream = None
        logger.info("assistant_orchestrator_initialized")
    
    async def start(self):
        """Start the assistant and open audio stream"""
        logger.info("assistant_starting")
        self.stream = self.audio.start_stream()
    
    async def wait_for_wake_word(self) -> bool:
        """
        Listen continuously for wake word
        
        Returns:
            True when wake word is detected
        """
        while True:
            try:
                audio_chunk = await self.audio.read_chunk(self.stream)
                if self.wake_word.detect(audio_chunk):
                    logger.info("wake_word_detected")
                    return True
                await asyncio.sleep(0.01)  # Prevent CPU hogging
            except Exception as e:
                logger.error("wake_word_error", error=str(e))
                await asyncio.sleep(0.1)
    
    async def capture_command(self, duration: float = 5.0) -> str:
        """
        Capture and transcribe voice command
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            Transcribed command text (empty string if failed)
        """
        try:
            # Small delay to avoid capturing wake word itself
            await asyncio.sleep(0.3)
            
            # Record audio
            logger.info("recording_command", duration=duration)
            audio_data = await self.audio.record_command(duration)
            
            # Validate audio
            if audio_data is None or len(audio_data) == 0:
                logger.warning("empty_audio_captured")
                return ""
            
            # Transcribe
            logger.info("transcribing_audio")
            text = await self.stt.transcribe(audio_data)
            logger.info("transcription_complete", text=text[:100])  # ← Zkrácený log
            
            return text
            
        except Exception as e:
            logger.error("capture_command_error", error=str(e), exc_info=True)
            return ""
    
    def process_command(self, text: str) -> str:
        """
        Process command through handler
        
        Args:
            text: Command text
            
        Returns:
            Response text
        """
        if not text or len(text.strip()) == 0:
            return ""
        
        logger.info("processing_command", text=text[:100])  # ← Zkrácený log
        response = self.commands.process(text)
        logger.info("command_processed", response=response)
        
        return response
    
    async def stop(self):
        """Stop the assistant and cleanup resources"""
        logger.info("assistant_stopping")
        try:
            if self.stream:
                self.audio.stop_stream()
        except Exception as e:
            logger.error("stop_error", error=str(e))
