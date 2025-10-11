"""Dependency injection container"""

import os
from dotenv import load_dotenv
from src.core.config.settings import load_config
from src.core.logging.logger import setup_logging
from src.infrastructure.adapters.audio.sounddevice_capture import SoundDeviceCapture
from src.infrastructure.adapters.wake_word.openwakeword_adapter import OpenWakeWordAdapter
from src.infrastructure.adapters.stt.hybrid_stt_adapter import HybridSTTAdapter
from src.infrastructure.adapters.ai.hybrid_handler import HybridAIHandler
from src.application.services.assistant_orchestrator import AssistantOrchestrator
from src.interfaces.cli.console_ui import ConsoleUI
import structlog

logger = structlog.get_logger()
load_dotenv()

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
                gain=3.0
            )
        return self._audio_input

    def wake_word_detector(self):
        if not self._wake_word_detector:
            self._wake_word_detector = OpenWakeWordAdapter(
                keywords=self.config.wake_word.keywords,
                threshold=float(self.config.wake_word.threshold)
            )
        return self._wake_word_detector

    def stt_engine(self):
        """Hybrid STT: Groq Whisper primary, lokální Whisper fallback"""
        if not self._stt_engine:
            groq_key = os.getenv("GROQ_API_KEY", "")
            self._stt_engine = HybridSTTAdapter(
                groq_api_key=groq_key,
                whisper_model=self.config.stt.model,
                language=self.config.stt.language
            )
            if groq_key:
                logger.info("stt_mode", mode="hybrid_groq_primary")
            else:
                logger.info("stt_mode", mode="local_only_no_api_key")
        return self._stt_engine

    def command_handler(self):
        if not self._command_handler:
            # Hybrid AI Handler s inteligentním routerem
            openai_api_key = os.getenv("OPENAI_API_KEY")
            user_preference = os.getenv("AI_PREFERENCE", None)  # 'local_only', 'cloud_only', or None
            
            self._command_handler = HybridAIHandler(
                api_key=openai_api_key,
                user_preference=user_preference
            )
            logger.info("hybrid_ai_handler_initialized", 
                       router="intelligent_5phase",
                       preference=user_preference)
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
