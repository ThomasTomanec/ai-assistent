"""
Groq Whisper STT adapter - super rychlý a zdarma!
Vylepšeno: async/sync fix, config z UserConfig, retry logic
"""

import structlog
import io
import wave
import asyncio
import time
from groq import Groq
from src.core.ports.i_stt_engine import ISTTEngine
from src.core.exceptions import STTError

logger = structlog.get_logger()


class GroqWhisperAdapter(ISTTEngine):
    """
    STT adapter pro Groq Whisper API.
    Extrémně rychlý (0.1-0.3s latence) a zdarma.
    """

    def __init__(self, api_key: str, language: str = "cs",
                 sample_rate: int = 16000, user_config=None):
        """
        Args:
            api_key: Groq API klíč
            language: Jazyk pro rozpoznávání (cs = čeština)
            sample_rate: Sample rate audia (16000 Hz)
            user_config: UserConfig instance pro načítání konfigurace
        """
        self.client = Groq(api_key=api_key)
        self.language = language
        self.sample_rate = sample_rate

        # Load config
        if user_config:
            self.model = user_config.get('audio.stt.groq_model', 'whisper-large-v3-turbo')
            self.max_retries = user_config.get('audio.stt.max_retries', 3)
        else:
            self.model = 'whisper-large-v3-turbo'
            self.max_retries = 3

        logger.info("groq_whisper_initialized",
                   language=language,
                   sample_rate=sample_rate,
                   model=self.model)

    def _convert_to_wav(self, audio_data: bytes) -> bytes:
        """
        Převede raw PCM audio na WAV formát s hlavičkami.

        Args:
            audio_data: Raw PCM audio data (int16)

        Returns:
            WAV audio data s hlavičkami
        """
        wav_buffer = io.BytesIO()

        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data)

        return wav_buffer.getvalue()

    def _transcribe_sync(self, audio_data: bytes) -> str:
        """
        Synchronní transcribe (volá Groq API).
        Spouští se v executoru aby neblokovalo async loop.

        Args:
            audio_data: Audio data (raw PCM)

        Returns:
            Rozpoznaný text
        """
        # Převeď raw PCM na WAV formát
        wav_data = self._convert_to_wav(audio_data)

        # Vytvoř file-like objekt
        audio_file = io.BytesIO(wav_data)
        audio_file.name = "audio.wav"

        # Zavolej Groq Whisper API (sync)
        transcription = self.client.audio.transcriptions.create(
            file=audio_file,
            model=self.model,
            language=self.language,
            response_format="text"
        )

        return transcription.strip()

    def _transcribe_with_retry(self, audio_data: bytes) -> str:
        """
        Transcribe s retry logikou.

        Args:
            audio_data: Audio data

        Returns:
            Rozpoznaný text
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return self._transcribe_sync(audio_data)

            except Exception as e:
                last_error = e

                if attempt == self.max_retries - 1:
                    raise

                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(
                    "groq_stt_retry",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    wait_seconds=wait_time,
                    error=str(e)
                )
                time.sleep(wait_time)

        raise last_error

    async def transcribe(self, audio_data: bytes) -> str:
        """
        Převede zvuk na text pomocí Groq Whisper (async wrapper).

        Args:
            audio_data: Audio data (raw PCM)

        Returns:
            Rozpoznaný text
        """
        try:
            logger.info("groq_transcribing", size=len(audio_data))

            # Spusť sync transcribe v executoru (neblocků async loop)
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                None,
                self._transcribe_with_retry,
                audio_data
            )

            logger.info("groq_complete", text=text[:100], length=len(text))
            return text

        except Exception as e:
            logger.error("groq_transcription_error",
                        error=str(e),
                        error_type=type(e).__name__)
            raise STTError(f"Groq transcription failed: {e}") from e
