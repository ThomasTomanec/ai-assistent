# src/core/config/container.py

"""
Dependency Injection Container - Refactored for maintainability
"""

import structlog
import os
from typing import Optional
from dotenv import load_dotenv

# Core imports
from src.core.config.user_config import get_user_config, UserConfig
from src.core.exceptions import ContainerInitializationError

# Infrastructure services
from src.infrastructure.services import TimeService, LocationService

# Application services
from src.application.services.context_builder import ContextBuilder
from src.application.services.assistant_orchestrator import AssistantOrchestrator

# AI adapters
from src.infrastructure.adapters.ai.cloud_model_handler import CloudModelHandler
from src.infrastructure.adapters.ai.local_model_handler import LocalModelHandler
from src.infrastructure.adapters.ai.hybrid_handler import HybridAIHandler

# Audio adapters
from src.infrastructure.adapters.audio.sounddevice_capture import SoundDeviceCapture
from src.infrastructure.adapters.audio.vad import VADRecorder, RecordingConfig
from src.infrastructure.adapters.wake_word.openwakeword_adapter import OpenWakeWordAdapter
from src.infrastructure.adapters.stt.hybrid_stt_adapter import HybridSTTAdapter

# Interface
from src.interfaces.cli.console_ui import ConsoleUI

logger = structlog.get_logger()


class Container:
    """
    Dependency Injection Container
    Manages lifecycle and dependencies of all application components.
    """

    def __init__(self):
        """Initialize container with all dependencies"""
        logger.info("container_initialization_started")

        try:
            # Step 1: Environment and configuration
            self._load_environment()
            self.user_config = self._load_user_config()

            # Step 2: Core infrastructure services
            self.location_service = self._create_location_service()
            self.time_service = self._create_time_service()

            # Step 3: Application services
            self.context_builder = self._create_context_builder()

            # Step 4: AI handlers
            self.cloud_handler = self._create_cloud_handler()
            self.local_handler = self._create_local_handler()
            self.command_handler = self._create_hybrid_handler()

            # Step 5: Audio pipeline
            self.audio_input = self._create_audio_input()
            self.vad_recorder = self._create_vad_recorder()
            self.wake_word_detector = self._create_wake_word_detector()
            self.stt_engine = self._create_stt_engine()

            # Step 6: Main orchestrator
            self.orchestrator = self._create_orchestrator()

            logger.info("container_initialization_completed")

        except Exception as e:
            logger.error("container_initialization_failed", error=str(e), exc_info=True)
            raise ContainerInitializationError(f"Failed to initialize container: {e}") from e

    # ========================================
    # ENVIRONMENT & CONFIG
    # ========================================

    def _load_environment(self) -> None:
        """Load environment variables from .env file"""
        try:
            load_dotenv()
            openai_key_present = bool(os.getenv("OPENAI_API_KEY"))
            groq_key_present = bool(os.getenv("GROQ_API_KEY"))

            logger.info(
                "environment_loaded",
                openai_key_present=openai_key_present,
                groq_key_present=groq_key_present
            )

            if not (openai_key_present or groq_key_present):
                logger.warning(
                    "no_api_keys_configured",
                    message="Neither OpenAI nor Groq API keys found. AI features may not work."
                )

        except Exception as e:
            logger.error("environment_load_failed", error=str(e))
            pass

    def _load_user_config(self) -> UserConfig:
        """Load and validate user configuration"""
        try:
            config = get_user_config()
            logger.info("user_config_loaded")
            return config
        except Exception as e:
            logger.error("user_config_load_failed", error=str(e))
            raise ContainerInitializationError(f"Failed to load user config: {e}") from e

    # ========================================
    # INFRASTRUCTURE SERVICES
    # ========================================

    def _create_location_service(self) -> LocationService:
        """Create location detection service"""
        try:
            service = LocationService()
            logger.debug("location_service_created")
            return service
        except Exception as e:
            logger.error("location_service_creation_failed", error=str(e))
            raise

    def _create_time_service(self) -> TimeService:
        """Create time service with appropriate timezone"""
        try:
            timezone = self.location_service.get_timezone(self.user_config)
            service = TimeService(timezone=timezone)
            logger.debug("time_service_created", timezone=timezone)
            return service
        except Exception as e:
            logger.warning("time_service_fallback_to_default", error=str(e))
            return TimeService(timezone='Europe/Prague')

    # ========================================
    # APPLICATION SERVICES
    # ========================================

    def _create_context_builder(self) -> ContextBuilder:
        """Create context builder for AI prompts"""
        try:
            builder = ContextBuilder(
                user_config=self.user_config,
                time_service=self.time_service,
                location_service=self.location_service
            )
            logger.debug("context_builder_created")
            return builder
        except Exception as e:
            logger.error("context_builder_creation_failed", error=str(e))
            raise

    # ========================================
    # AI HANDLERS
    # ========================================

    def _create_cloud_handler(self) -> CloudModelHandler:
        """Create cloud AI model handler (OpenAI)"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            provider = self.user_config.get('models.cloud.provider', 'openai')
            streaming = self.user_config.get('models.cloud.streaming', True)

            if not api_key:
                logger.warning("openai_api_key_missing",
                               message="Cloud AI may not work without API key")

            handler = CloudModelHandler(
                context_builder=self.context_builder,
                api_key=api_key,
                provider=provider,
                streaming=streaming
            )

            logger.debug("cloud_handler_created", provider=provider, streaming=streaming)
            return handler
        except Exception as e:
            logger.error("cloud_handler_creation_failed", error=str(e))
            raise

    def _create_local_handler(self) -> LocalModelHandler:
        """Create local AI model handler (Ollama)"""
        try:
            handler = LocalModelHandler()
            logger.debug("local_handler_created")
            return handler
        except Exception as e:
            logger.error("local_handler_creation_failed", error=str(e))
            raise

    def _create_hybrid_handler(self) -> HybridAIHandler:
        """Create hybrid AI handler with intelligent routing"""
        try:
            strategy = self.user_config.get('routing.strategy', 'intelligent')
            handler = HybridAIHandler(
                cloud_handler=self.cloud_handler,
                local_handler=self.local_handler,
                user_preference=strategy
            )
            logger.debug("hybrid_handler_created", strategy=strategy)
            return handler
        except Exception as e:
            logger.error("hybrid_handler_creation_failed", error=str(e))
            raise

    # ========================================
    # AUDIO PIPELINE
    # ========================================

    def _create_audio_input(self) -> SoundDeviceCapture:
        """Create audio input device"""
        try:
            audio_config = self.user_config.get('audio', {})

            device = SoundDeviceCapture(
                sample_rate=audio_config.get('sample_rate', 16000),
                channels=audio_config.get('channels', 1),
                chunk_size=audio_config.get('chunk_size', 1280),
                gain=audio_config.get('gain', 6.0)
            )

            logger.debug(
                "audio_input_created",
                sample_rate=audio_config.get('sample_rate', 16000),
                gain=audio_config.get('gain', 6.0)
            )

            return device
        except Exception as e:
            logger.error("audio_input_creation_failed", error=str(e))
            raise

    def _create_vad_recorder(self) -> VADRecorder:
        """
        Create VAD recorder with ULTRA-FAST configuration (0.3s trailing).
        Clean production version without debug banner.
        """
        try:
            vad_config_dict = self.user_config.get('audio.vad', {})

            # ULTRA-FAST defaults - overridable from config
            vad_config = RecordingConfig(
                # Duration (ULTRA-FAST)
                max_duration=vad_config_dict.get('max_duration', 15.0),
                silence_duration=vad_config_dict.get('silence_duration', 1.0),  # Initial
                quick_silence=vad_config_dict.get('quick_silence', 0.3),  # ⚡ ULTRA-FAST: 0.3s
                min_speech_frames=vad_config_dict.get('min_speech_frames', 3),  # ⚡ ULTRA-LOW: 3

                # Proximity - DISABLED for production
                proximity_enabled=vad_config_dict.get('proximity_enabled', False),
                proximity_threshold=vad_config_dict.get('proximity_threshold', 2.5),
                proximity_margin=vad_config_dict.get('proximity_margin', 0.7),

                # Quality - LIBERAL for production
                min_volume_threshold=vad_config_dict.get('min_volume_threshold', 0.0),
                max_volume_threshold=vad_config_dict.get('max_volume_threshold', 1.0),
                noise_gate_enabled=vad_config_dict.get('noise_gate_enabled', False),
                noise_gate_ratio=vad_config_dict.get('noise_gate_ratio', 1.0),

                # VAD (legacy, not used)
                vad_aggressiveness=vad_config_dict.get('vad_aggressiveness', 0),
                sample_rate=self.user_config.get('audio.sample_rate', 16000),
                frame_duration_ms=vad_config_dict.get('frame_duration_ms', 30),

                # Advanced
                adaptive_timeout_enabled=vad_config_dict.get('adaptive_timeout', True)
            )

            recorder = VADRecorder(
                audio_input=self.audio_input,
                config=vad_config
            )

            # Clean logging without banner
            logger.debug(
                "vad_recorder_created_ultrafast",
                trailing_silence=vad_config.quick_silence,
                initial_silence=vad_config.silence_duration,
                min_speech_frames=vad_config.min_speech_frames,
                vad_type="double_threshold_rms_0.3s"
            )

            return recorder

        except Exception as e:
            logger.error("vad_recorder_creation_failed", error=str(e))
            raise

    def _create_wake_word_detector(self) -> OpenWakeWordAdapter:
        """Create wake word detection adapter"""
        try:
            keywords = self.user_config.get('audio.wake_word_models', ['alexa'])
            threshold = self.user_config.get('assistant.wake_word_threshold', 0.5)

            detector = OpenWakeWordAdapter(
                keywords=keywords,
                threshold=threshold
            )

            logger.debug(
                "wake_word_detector_created",
                keywords=keywords,
                threshold=threshold
            )

            return detector
        except Exception as e:
            logger.error("wake_word_detector_creation_failed", error=str(e))
            raise

    def _create_stt_engine(self) -> HybridSTTAdapter:
        """Create speech-to-text engine"""
        try:
            groq_api_key = os.getenv("GROQ_API_KEY", "")
            whisper_model = self.user_config.get('audio.stt.whisper_model', 'small')
            language = self.user_config.get('user.language', 'cs')

            if not groq_api_key:
                logger.warning("groq_api_key_missing",
                               message="STT will fallback to local Whisper")

            engine = HybridSTTAdapter(
                groq_api_key=groq_api_key,
                whisper_model=whisper_model,
                language=language
            )

            logger.debug(
                "stt_engine_created",
                whisper_model=whisper_model,
                language=language,
                has_groq_key=bool(groq_api_key)
            )

            return engine
        except Exception as e:
            logger.error("stt_engine_creation_failed", error=str(e))
            raise

    # ========================================
    # ORCHESTRATOR
    # ========================================

    def _create_orchestrator(self) -> AssistantOrchestrator:
        """Create main assistant orchestrator"""
        try:
            orchestrator = AssistantOrchestrator(
                audio_input=self.audio_input,
                wake_word_detector=self.wake_word_detector,
                stt_engine=self.stt_engine,
                command_handler=self.command_handler,
                vad_recorder=self.vad_recorder,
                vad_config=None
            )

            logger.debug("orchestrator_created")
            return orchestrator
        except Exception as e:
            logger.error("orchestrator_creation_failed", error=str(e))
            raise

    # ========================================
    # PUBLIC INTERFACE
    # ========================================

    def console_ui(self) -> ConsoleUI:
        """
        Create console UI interface

        Returns:
            ConsoleUI instance configured with orchestrator
        """
        try:
            ui = ConsoleUI(
                orchestrator=self.orchestrator,
                user_config=self.user_config
            )
            logger.debug("console_ui_created")
            return ui
        except Exception as e:
            logger.error("console_ui_creation_failed", error=str(e))
            raise


def setup_container() -> Container:
    """
    Setup and initialize dependency injection container

    Returns:
        Fully initialized Container instance

    Raises:
        ContainerInitializationError: If initialization fails
    """
    return Container()
