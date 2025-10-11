"""
Cloud AI model handler - čistá odpovědnost za API komunikaci
"""

import structlog
import os
import httpx
from openai import OpenAI
from src.core.ports.i_command_handler import ICommandHandler
from src.application.services.context_builder import ContextBuilder

logger = structlog.get_logger()

class CloudModelHandler(ICommandHandler):
    """Handler pro komunikaci s cloudovým AI API"""

    def __init__(self, context_builder: ContextBuilder, api_key: str = None,
                 provider: str = "openai", streaming: bool = True):
        """
        Args:
            context_builder: Service pro sestavování kontextu
            api_key: API klíč pro cloudovou službu
            provider: Poskytovatel ('openai', 'anthropic', atd.)
            streaming: Použít streaming pro rychlejší odpovědi
        """
        self.context_builder = context_builder
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.provider = provider
        self.streaming = streaming
        self.client = OpenAI(api_key=self.api_key)
        self.internet_available = self._check_internet()
        logger.info("cloud_model_handler_initialized",
                   provider=provider,
                   streaming=streaming,
                   internet=self.internet_available)

    def _check_internet(self) -> bool:
        """Zkontroluj připojení k internetu a OpenAI API"""
        try:
            httpx.get("https://api.openai.com", timeout=3.0)
            return True
        except:
            return False

    def process(self, text: str) -> str:
        """
        Zpracuje dotaz pomocí cloudového AI.

        Args:
            text: Text příkazu

        Returns:
            Odpověď z cloudového modelu
        """
        # Zkus rychlou odpověď pro jednoduché časové dotazy
        quick_answer = self.context_builder.get_quick_time_answer(text)
        if quick_answer:
            logger.info("quick_time_answer_provided", query=text[:50])
            return quick_answer

        # Check internet
        if not self._check_internet():
            logger.warning("cloud_offline_fallback")
            return "[Cloud nedostupný - zkusím lokální model]"

        logger.info("processing_with_cloud_model", text=text[:100], streaming=self.streaming)

        try:
            if self.provider == "openai":
                if self.streaming:
                    return self._process_openai_streaming(text)
                else:
                    return self._process_openai(text)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            logger.error("cloud_model_error", error=str(e))
            return "[Cloud AI selhalo - zkusím lokální model]"

    def _process_openai_streaming(self, text: str) -> str:
        """Zpracování přes OpenAI API se streamingem"""
        try:
            # Získej system prompt z context builderu
            system_prompt = self.context_builder.build_system_prompt()

            stream = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.7,
                max_tokens=500,
                stream=True
            )

            full_response = ""
            first_chunk_received = False

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content

                    if not first_chunk_received:
                        logger.debug("first_chunk_received", latency="low")
                        first_chunk_received = True

                    # ❌ SMAZÁNO: print(content, end="", flush=True)
                    # Console UI to zobrazí samo

            logger.debug("streaming_complete", response_length=len(full_response))
            return full_response.strip()

        except Exception as e:
            logger.error("openai_streaming_error", error=str(e))
            return "[Cloud AI selhalo - zkusím lokální model]"

    def _process_openai(self, text: str) -> str:
        """Zpracování přes OpenAI API bez streamingu"""
        try:
            system_prompt = self.context_builder.build_system_prompt()

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.7,
                max_tokens=500
            )

            answer = response.choices[0].message.content.strip()
            logger.debug("cloud_model_response", response_length=len(answer))
            return answer

        except Exception as e:
            logger.error("openai_api_error", error=str(e))
            return "[Cloud AI selhalo - zkusím lokální model]"
