"""
Hybrid STT with Groq primary, Whisper fallback
Vylepšeno: lepší error handling, používá custom exceptions
"""

import structlog
from src.core.ports.i_stt_engine import ISTTEngine
from src.infrastructure.adapters.stt.groq_whisper_adapter import GroqWhisperAdapter
from src.infrastructure.adapters.stt.whisper_adapter import WhisperAdapter
from src.core.exceptions import STTError

logger = structlog.get_logger()


class HybridSTTAdapter(ISTTEngine):
    """
    Hybrid STT: Groq Whisper primary (rychlý, zdarma), lokální Whisper fallback
    """

    def __init__(self, groq_api_key: str = "", whisper_model: str = "small",
                 language: str = "cs", user_config=None):
        """
        Args:
            groq_api_key: Groq API klíč
            whisper_model: Whisper model size (tiny, base, small, medium)
            language: Jazyk (cs, en, ...)
            user_config: UserConfig instance
        """
        self.groq_enabled = bool(groq_api_key)
        self.user_config = user_config

        # Primary: Groq (pokud je API key)
        if self.groq_enabled:
            self.primary = GroqWhisperAdapter(
                api_key=groq_api_key,
                language=language,
                user_config=user_config
            )
            logger.info("hybrid_stt_groq_enabled")
        else:
            self.primary = None
            logger.info("hybrid_stt_groq_disabled", reason="no_api_key")

        # Fallback: Lokální Whisper (vždy)
        self.fallback = WhisperAdapter(
            model_size=whisper_model,
            language=language,
            user_config=user_config
        )

        logger.info("hybrid_stt_initialized",
                   primary="groq" if self.groq_enabled else "local_whisper",
                   fallback="local_whisper")

    async def transcribe(self, audio_data: bytes) -> str:
        """
        Transcribe s fallback strategií.

        Args:
            audio_data: Audio data

        Returns:
            Rozpoznaný text
        """
        # Zkus primární (Groq) - pokud je dostupný
        if self.primary:
            try:
                logger.info("trying_groq_stt")
                text = await self.primary.transcribe(audio_data)

                if text and len(text.strip()) > 0:
                    logger.info("groq_stt_success", length=len(text))
                    return text
                else:
                    logger.warning("groq_stt_empty_result")

            except STTError as e:
                logger.warning("groq_stt_failed_fallback_to_local", error=str(e))
            except Exception as e:
                logger.error("groq_stt_unexpected_error", error=str(e))

        # Fallback na lokální Whisper
        try:
            logger.info("using_local_whisper_fallback")
            text = await self.fallback.transcribe(audio_data)

            if text and len(text.strip()) > 0:
                logger.info("local_whisper_success", length=len(text))
                return text
            else:
                logger.warning("local_whisper_empty_result")
                return ""

        except Exception as e:
            logger.error("local_whisper_failed", error=str(e))
            raise STTError(f"All STT engines failed: {e}") from e
