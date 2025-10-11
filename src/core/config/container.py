"""
Dependency Injection Container
"""

import structlog
import os
from dotenv import load_dotenv
from src.core.config.user_config import get_user_config
from src.infrastructure.services.core.time_service import TimeService
from src.infrastructure.services.core.location_service import LocationService
from src.application.services.context_builder import ContextBuilder
from src.application.services.assistant_orchestrator import AssistantOrchestrator
from src.infrastructure.adapters.ai.cloud_model_handler import CloudModelHandler
from src.infrastructure.adapters.ai.local_model_handler import LocalModelHandler
from src.infrastructure.adapters.ai.hybrid_handler import HybridAIHandler
from src.infrastructure.adapters.audio.sounddevice_capture import SoundDeviceCapture
from src.infrastructure.adapters.wake_word.openwakeword_adapter import OpenWakeWordAdapter
from src.infrastructure.adapters.stt.hybrid_stt_adapter import HybridSTTAdapter
from src.interfaces.cli.console_ui import ConsoleUI

logger = structlog.get_logger()

class Container:
    """Dependency Injection Container"""

    def __init__(self):
        """Inicializuj všechny dependencies"""
        logger.info("setting_up_container")

        # Načti .env soubor
        load_dotenv()
        logger.info("dotenv_loaded",
                   openai_key_present=bool(os.getenv("OPENAI_API_KEY")),
                   groq_key_present=bool(os.getenv("GROQ_API_KEY")))

        # 1. Načti user config
        self.user_config = get_user_config()

        # 2. Vytvoř location service (NOVÉ)
        self.location_service = LocationService()

        # 3. Získej aktuální lokaci
        if self.user_config.get('location.auto_detect', True):
            location = self.location_service.get_current_location()
            timezone = location['timezone']
        else:
            timezone = self.user_config.get('location.manual.timezone', 'Europe/Prague')

        # 4. Vytvoř time service s dynamickým timezone
        self.time_service = TimeService(timezone=timezone)

        # 5. Vytvoř context builder (s location service)
        self.context_builder = ContextBuilder(
            self.user_config,
            self.time_service,
            self.location_service  # NOVÉ
        )

        # 6. Vytvoř cloud handler
        self.cloud_handler = CloudModelHandler(
            context_builder=self.context_builder,
            api_key=os.getenv("OPENAI_API_KEY"),
            streaming=True
        )

        # 7. Vytvoř local handler
        self.local_handler = LocalModelHandler()

        # 8. Vytvoř hybrid AI handler
        self.command_handler = HybridAIHandler(
            cloud_handler=self.cloud_handler,
            local_handler=self.local_handler,
            user_preference=None
        )

        # 9. Vytvoř audio input
        self.audio_input = SoundDeviceCapture(
            sample_rate=self.user_config.get('audio.sample_rate', 16000),
            channels=1,
            chunk_size=1280,
            gain=self.user_config.get('audio.gain', 6.0)
        )

        # 10. Vytvoř wake word detector
        wake_word_models = self.user_config.get('audio.wake_word_models', ['alexa'])
        wake_word_threshold = self.user_config.get('assistant.wake_word_threshold', 0.5)

        self.wake_word_detector = OpenWakeWordAdapter(
            keywords=wake_word_models,
            threshold=wake_word_threshold
        )

        # 11. Vytvoř STT engine
        groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.stt_engine = HybridSTTAdapter(
            groq_api_key=groq_api_key,
            whisper_model="small",
            language=self.user_config.get('user.language', 'cs')
        )

        # 12. Vytvoř orchestrator
        self.orchestrator = AssistantOrchestrator(
            audio_input=self.audio_input,
            wake_word_detector=self.wake_word_detector,
            stt_engine=self.stt_engine,
            command_handler=self.command_handler
        )

        logger.info("container_setup_complete")

    def console_ui(self) -> ConsoleUI:
        """Vytvoř ConsoleUI s user config"""
        return ConsoleUI(
            orchestrator=self.orchestrator,
            user_config=self.user_config
        )

def setup_container() -> Container:
    """Sestaví container"""
    return Container()
