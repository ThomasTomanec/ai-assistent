"""Dependency injection container"""

from src.core.config.settings import load_config
from src.core.logging.logger import setup_logging
from src.infrastructure.adapters.audio.sounddevice_capture import SoundDeviceCapture
from src.infrastructure.adapters.wake_word.openwakeword_adapter import OpenWakeWordAdapter
from src.infrastructure.adapters.stt.whisper_adapter import WhisperAdapter
from src.infrastructure.adapters.tts.piper_adapter import PiperAdapter
from src.infrastructure.adapters.commands.simple_handler import SimpleCommandHandler
from src.application.services.assistant_orchestrator import AssistantOrchestrator
from src.interfaces.cli.console_ui import ConsoleUI

class Container:
    """Simple dependency injection container"""
    
    def __init__(self):
        # Load config
        self.config = load_config()
        setup_logging(
            level=self.config.logging.level,
            log_format=self.config.logging.format,
            log_file=self.config.logging.file
        )
        
        # Infrastructure (lazy loading)
        self._audio_input = None
        self._wake_word_detector = None
        self._stt_engine = None
        self._tts_engine = None
        self._command_handler = None
        
        # Application
        self._orchestrator = None
        
        # Interfaces
        self._console_ui = None
    
    def audio_input(self):
        if not self._audio_input:
            self._audio_input = SoundDeviceCapture(
                sample_rate=self.config.audio.sample_rate,
                channels=self.config.audio.channels,
                chunk_size=self.config.audio.chunk_size,
                device=self.config.audio.input_device,
                gain=3.0  # ← ZMĚNĚNO z 10.0 na 3.0
            )
        return self._audio_input
    
    def wake_word_detector(self):
        if not self._wake_word_detector:
            self._wake_word_detector = OpenWakeWordAdapter(
                keywords=self.config.wake_word.keywords,
                threshold=0.3
            )
        return self._wake_word_detector
    
    def stt_engine(self):
        if not self._stt_engine:
            self._stt_engine = WhisperAdapter(
                model_size=self.config.stt.model,
                language=self.config.stt.language
            )
        return self._stt_engine
    
    def tts_engine(self):
        if not self._tts_engine:
            self._tts_engine = PiperAdapter(
                voice=self.config.tts.voice,
                rate=self.config.tts.rate
            )
        return self._tts_engine
    
    def command_handler(self):
        if not self._command_handler:
            self._command_handler = SimpleCommandHandler()
        return self._command_handler
    
    def orchestrator(self):
        if not self._orchestrator:
            self._orchestrator = AssistantOrchestrator(
                audio_input=self.audio_input(),
                wake_word_detector=self.wake_word_detector(),
                stt_engine=self.stt_engine(),
                command_handler=self.command_handler()
            )
        return self._orchestrator
    
    def console_ui(self):
        if not self._console_ui:
            self._console_ui = ConsoleUI(
                orchestrator=self.orchestrator()
            )
        return self._console_ui

def setup_container() -> Container:
    """Setup and return DI container"""
    return Container()
