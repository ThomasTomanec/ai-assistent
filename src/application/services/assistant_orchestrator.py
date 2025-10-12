"""Assistant Orchestrator with streaming callback support"""

import asyncio
import structlog
from typing import Callable, Optional
from src.core.ports.i_audio_input import IAudioInput
from src.core.ports.i_wake_word_detector import IWakeWordDetector
from src.core.ports.i_stt_engine import ISTTEngine
from src.core.ports.i_command_handler import ICommandHandler
from src.infrastructure.adapters.audio.vad_recorder import VADRecorder

logger = structlog.get_logger()


class AssistantOrchestrator:
    """Orchestrates voice assistant components with streaming support"""

    def __init__(self, audio_input: IAudioInput,
                 wake_word_detector: IWakeWordDetector,
                 stt_engine: ISTTEngine,
                 command_handler: ICommandHandler):
        self.audio = audio_input
        self.wake_word = wake_word_detector
        self.stt = stt_engine
        self.commands = command_handler
        self.stream = None
        self.vad_recorder = VADRecorder(audio_input, stream=self.stream)

        # Streaming callback
        self.response_callback: Optional[Callable] = None

    def set_response_callback(self, callback: Callable):
        """
        Set callback for streaming response chunks.
        Propagates to command handler.

        Args:
            callback: Function(chunk: str, is_final: bool)
        """
        self.response_callback = callback

        # Propagate to command handler if it supports streaming
        if hasattr(self.commands, 'set_response_callback'):
            self.commands.set_response_callback(callback)
            logger.debug("response_callback_set_on_command_handler")
        else:
            logger.debug("command_handler_does_not_support_streaming")

    async def start(self):
        """Start the assistant"""
        logger.info("assistant_starting")
        self.stream = self.audio.start_stream()
        self.vad_recorder.stream = self.stream

    async def stop(self):
        """Stop the assistant"""
        logger.info("assistant_stopping")
        if self.stream:
            self.audio.stop_stream()

    async def wait_for_wake_word(self) -> bool:
        """
        Wait for wake word detection.

        Returns:
            True if wake word detected, False otherwise
        """
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

        Returns:
            Transcribed text or empty string on error
        """
        try:
            # Small pause after wake word
            await asyncio.sleep(0.3)

            # Record audio
            audio_data = await self.vad_recorder.record_until_silence(max_duration=10)

            if audio_data is None or len(audio_data) == 0:
                logger.warning("empty_audio_captured")
                return ""

            # Transcribe
            logger.info("transcribing_audio", size=len(audio_data))
            text = await self.stt.transcribe(audio_data)

            logger.info("transcription_complete", text=text[:100])
            return text

        except Exception as e:
            logger.error("capture_command_error", error=str(e), exc_info=True)
            return ""

    def process_command(self, text: str) -> str:
        """
        Process command and return response.

        Args:
            text: Command text from STT

        Returns:
            Response text
        """
        if not text or len(text.strip()) == 0:
            return ""

        logger.info("processing_command", text=text[:100])

        try:
            # Process through command handler (streaming callbacks happen here)
            response = self.commands.process(text)

            logger.info("command_processed", response=response[:100])
            return response

        except Exception as e:
            logger.error("command_processing_error", error=str(e), exc_info=True)
            return f"Omlouvám se, nastala chyba: {str(e)}"
