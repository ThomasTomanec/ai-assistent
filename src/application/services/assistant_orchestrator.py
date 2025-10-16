# src/application/services/assistant_orchestrator.py

"""Assistant Orchestrator - production version without debug output"""

import asyncio
import structlog
from typing import Callable, Optional

from src.core.ports.i_audio_input import IAudioInput
from src.core.ports.i_wake_word_detector import IWakeWordDetector
from src.core.ports.i_stt_engine import ISTTEngine
from src.core.ports.i_command_handler import ICommandHandler
from src.infrastructure.adapters.audio.vad import VADRecorder, RecordingConfig

logger = structlog.get_logger()


class AssistantOrchestrator:
    """
    Orchestrates voice assistant components with streaming support.
    """

    def __init__(
            self,
            audio_input: IAudioInput,
            wake_word_detector: IWakeWordDetector,
            stt_engine: ISTTEngine,
            command_handler: ICommandHandler,
            vad_recorder: Optional[VADRecorder] = None,
            vad_config: Optional[RecordingConfig] = None
    ):
        self.audio = audio_input
        self.wake_word = wake_word_detector
        self.stt = stt_engine
        self.commands = command_handler
        self.stream = None

        if vad_recorder:
            self.vad_recorder = vad_recorder
            logger.debug("using_provided_vad_recorder")
        else:
            config = vad_config or RecordingConfig()
            self.vad_recorder = VADRecorder(
                audio_input=audio_input,
                stream=self.stream,
                config=config
            )
            logger.debug("created_new_vad_recorder")

        self.response_callback: Optional[Callable] = None
        self._calibrated = False

    def set_response_callback(self, callback: Callable):
        """Set callback for streaming response chunks."""
        self.response_callback = callback

        if hasattr(self.commands, 'set_response_callback'):
            self.commands.set_response_callback(callback)
            logger.debug("response_callback_set_on_command_handler")
        else:
            logger.debug("command_handler_does_not_support_streaming")

    async def start(self):
        """Start the assistant."""
        logger.info("assistant_starting")

        self.stream = self.audio.start_stream()
        self.vad_recorder.stream = self.stream

        if not self._calibrated:
            try:
                logger.info("calibrating_vad_background")
                background = await self.vad_recorder.calibrate_background(
                    duration=2.0,
                    auto_adjust=True
                )
                self._calibrated = True
                logger.info("vad_calibrated", background_noise=round(background, 6))
            except Exception as e:
                logger.warning("vad_calibration_failed", error=str(e))

    async def stop(self):
        """Stop the assistant"""
        logger.info("assistant_stopping")
        if self.stream:
            self.audio.stop_stream()

    async def wait_for_wake_word(self) -> bool:
        """Wait for wake word detection."""
        self.wake_word.reset()

        while True:
            try:
                audio_chunk = await self.audio.read_chunk(self.stream)

                if self.wake_word.detect(audio_chunk):
                    logger.info("wake_word_detected")
                    self.wake_word.reset()
                    return True

                await asyncio.sleep(0.01)

            except Exception as e:
                logger.error("wake_word_error", error=str(e))
                await asyncio.sleep(0.1)

    async def capture_command(self) -> str:
        """
        Capture and transcribe voice command.
        Clean production version without debug output.
        """
        try:
            # Small pause after wake word
            await asyncio.sleep(0.3)

            logger.info("capturing_command")
            audio_data, metrics = await self.vad_recorder.record_until_silence(
                max_duration=10.0
            )

            # Check if we got audio
            if audio_data is None or len(audio_data) == 0:
                logger.warning("empty_audio_captured",
                               speech_frames=metrics.speech_frames,
                               quality_score=metrics.quality_score)

                # Silent error for user - just return empty
                if metrics.speech_frames == 0:
                    print("❌ No speech detected")
                return ""

            # Log quality warning if needed
            if metrics.quality_score < 0.3:
                logger.warning("low_quality_audio", quality_score=metrics.quality_score)

            # Transcribe
            logger.info("transcribing_audio", size=len(audio_data))
            text = await self.stt.transcribe(audio_data)

            if text:
                logger.info("transcription_complete", text=text[:100])
            else:
                logger.warning("transcription_empty")

            return text

        except Exception as e:
            logger.error("capture_command_error", error=str(e), exc_info=True)
            return ""

    def process_command(self, text: str) -> str:
        """Process command and return response."""
        if not text or len(text.strip()) == 0:
            logger.debug("empty_command_text")
            return ""

        logger.info("processing_command", text=text[:100])

        try:
            response = self.commands.process(text)

            if response:
                logger.info("command_processed", response=response[:100])
            else:
                logger.warning("empty_command_response")

            return response

        except Exception as e:
            logger.error("command_processing_error", error=str(e), exc_info=True)
            return f"Omlouvám se, nastala chyba: {str(e)}"

    def get_last_recording_metrics(self):
        """Vrátí metriky z posledního nahrávání."""
        return self.vad_recorder.get_last_metrics()

    def get_statistics(self) -> dict:
        """Vrátí celkové statistiky orchestratoru."""
        return {
            'calibrated': self._calibrated,
            'vad_recorder': self.vad_recorder.get_statistics(),
            'stream_active': self.stream is not None
        }

    async def recalibrate_vad(self, duration: float = 2.0) -> None:
        """Ručně překalibruj VAD."""
        logger.info("recalibrating_vad")
        try:
            background = await self.vad_recorder.calibrate_background(
                duration=duration,
                auto_adjust=True
            )
            self._calibrated = True
            logger.info("vad_recalibrated", background=round(background, 6))
        except Exception as e:
            logger.error("recalibration_failed", error=str(e))
            raise
