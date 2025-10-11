"""
Cloud AI model handler pro složité dotazy
"""

import structlog
import os
import httpx
from datetime import datetime
from openai import OpenAI
from src.core.ports.i_command_handler import ICommandHandler

logger = structlog.get_logger()

class CloudModelHandler(ICommandHandler):
    """
    Handler pro zpracování složitých dotazů pomocí cloudového AI API.
    Podporuje streaming pro nízkou latenci.
    """

    def __init__(self, api_key: str = None, provider: str = "openai", streaming: bool = True):
        """
        Args:
            api_key: API klíč pro cloudovou službu
            provider: Poskytovatel ('openai', 'anthropic', atd.)
            streaming: Použít streaming pro rychlejší odpovědi
        """
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

    def _get_system_prompt(self) -> str:
        """
        Vytvoř system prompt s aktuálním datem a časem.

        Returns:
            System prompt obsahující aktuální datum a čas
        """
        now = datetime.now()

        # Český formát data a času
        day_names = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle']
        day_name = day_names[now.weekday()]

        current_datetime = f"{day_name}, {now.day}. {now.month}. {now.year}, {now.hour:02d}:{now.minute:02d}"

        return f"""Jsi inteligentní hlasový asistent. Odpovídej stručně a přesně v češtině.

Aktuální datum a čas: {current_datetime}

Pokud se uživatel ptá na čas, datum nebo den v týdnu, odpověz na základě těchto informací.
Při odpovědích o času používej 24hodinový formát."""

    def process(self, text: str) -> str:
        """
        Zpracuje složitý dotaz pomocí cloudového AI.
        Pokud není internet, vrátí placeholder pro lokální fallback.

        Args:
            text: Text příkazu

        Returns:
            Odpověď z cloudového modelu nebo placeholder
        """
        # Check internet při každém requestu
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
        """
        Zpracování přes OpenAI API se streamingem.
        Posílá odpověď průběžně (slovo po slovu).
        """
        try:
            stream = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": text}
                ],
                temperature=0.7,
                max_tokens=500,
                stream=True
            )

            # Sbírej odpověď průběžně
            full_response = ""
            first_chunk_received = False

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content

                    if not first_chunk_received:
                        logger.info("first_chunk_received", latency="low")
                        first_chunk_received = True

                    print(content, end="", flush=True)

            print()
            logger.info("streaming_complete", response=full_response[:100], length=len(full_response))

            return full_response.strip()

        except Exception as e:
            logger.error("openai_streaming_error", error=str(e))
            return "[Cloud AI selhalo - zkusím lokální model]"

    def _process_openai(self, text: str) -> str:
        """
        Zpracování přes OpenAI API bez streamingu (klasické).
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": text}
                ],
                temperature=0.7,
                max_tokens=500
            )

            answer = response.choices[0].message.content.strip()
            logger.info("cloud_model_response", response=answer[:100])
            return answer

        except Exception as e:
            logger.error("openai_api_error", error=str(e))
            return "[Cloud AI selhalo - zkusím lokální model]"
