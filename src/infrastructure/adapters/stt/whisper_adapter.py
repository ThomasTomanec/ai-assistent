"""
Whisper STT adapter with platform detection
Vylepšeno: config z UserConfig
"""

import asyncio
import numpy as np
import structlog
import sys
import platform
from src.core.ports.i_stt_engine import ISTTEngine
from src.core.exceptions import STTError

logger = structlog.get_logger()

# Platform detection
IS_APPLE_SILICON = (
    platform.machine() == "arm64" and
    sys.platform == "darwin"
)


class WhisperAdapter(ISTTEngine):
    """Speech-to-text using Whisper (MLX on M1, faster-whisper on others)"""

    def __init__(self, model_size: str = "base", language: str = "en", user_config=None):
        """
        Initialize Whisper STT

        Args:
            model_size: Model size (tiny, base, small, medium, large)
            language: Language code (en, cs, etc.)
            user_config: UserConfig instance
        """
        self.model_size = model_size
        self.language = language
        self.model = None
        self.user_config = user_config

        # Load config values
        if user_config:
            self.beam_size = user_config.get('audio.stt.whisper_beam_size', 1)
            self.vad_filter = user_config.get('audio.stt.whisper_vad_filter', True)
        else:
            self.beam_size = 1
            self.vad_filter = True

        # Load appropriate backend based on platform
        if IS_APPLE_SILICON:
            self._init_mlx_whisper()
        else:
            self._init_faster_whisper()

        logger.info(
            "whisper_adapter_initialized",
            model=model_size,
            language=language,
            backend=self.backend,
            beam_size=self.beam_size
        )

    def _init_mlx_whisper(self):
        """Initialize MLX Whisper for Apple Silicon"""
        try:
            import mlx_whisper
            self.mlx_whisper = mlx_whisper
            self.backend = "mlx"
            # Correct MLX community model path with -mlx suffix
            self.model_path = f"mlx-community/whisper-{self.model_size}-mlx"
            logger.info("mlx_whisper_initialized", model=self.model_path)
        except ImportError:
            logger.error("mlx_whisper_not_installed")
            raise ImportError("Install mlx-whisper: pip install mlx-whisper")

    def _init_faster_whisper(self):
        """Initialize faster-whisper for Linux/other platforms"""
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8"
            )
            self.backend = "faster-whisper"
            logger.info("faster_whisper_initialized")
        except ImportError:
            logger.error("faster_whisper_not_installed")
            raise ImportError("Install faster-whisper: pip install faster-whisper")

    async def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribe audio to text

        Args:
            audio_data: Audio data (int16 or float32)

        Returns:
            Transcribed text
        """
        try:
            # Convert to float32 if needed (both backends expect this)
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32768.0

            # Run transcription in executor to avoid blocking
            loop = asyncio.get_event_loop()

            if self.backend == "mlx":
                result = await loop.run_in_executor(
                    None,
                    self._transcribe_mlx,
                    audio_data
                )
            else:
                result = await loop.run_in_executor(
                    None,
                    self._transcribe_faster,
                    audio_data
                )

            logger.info("whisper_transcription_complete",
                       text=result[:100],
                       length=len(result))
            return result

        except Exception as e:
            logger.error("whisper_transcription_error",
                        error=str(e),
                        error_type=type(e).__name__)
            raise STTError(f"Whisper transcription failed: {e}") from e

    def _transcribe_mlx(self, audio_data: np.ndarray) -> str:
        """Transcribe using MLX Whisper"""
        result = self.mlx_whisper.transcribe(
            audio_data,
            path_or_hf_repo=self.model_path,
            language=self.language
        )
        return result["text"].strip()

    def _transcribe_faster(self, audio_data: np.ndarray) -> str:
        """Transcribe using faster-whisper"""
        segments, _ = self.model.transcribe(
            audio_data,
            language=self.language,
            beam_size=self.beam_size,
            vad_filter=self.vad_filter,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        text = " ".join([segment.text for segment in segments])
        return text.strip()
