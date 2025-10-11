"""
Lokální AI model handler s Ollama (Llama 3.2 3B)
"""

import structlog
import httpx
from typing import Optional
from src.core.ports.i_command_handler import ICommandHandler

logger = structlog.get_logger()

class LocalModelHandler(ICommandHandler):
    """
    Handler pro zpracování jednoduchých dotazů lokálním LLM (Ollama).

    Automaticky detekuje jestli Ollama běží:
    - Pokud ANO → použije lokální model (rychlé!)
    - Pokud NE → vrátí placeholder (eskaluje do cloudu)
    """

    def __init__(self, model: str = "llama3.2:3b", ollama_url: str = "http://localhost:11434"):
        """
        Args:
            model: Ollama model name (llama3.2:3b, qwen2.5:1.5b, atd.)
            ollama_url: URL Ollama API serveru
        """
        self.model = model
        self.ollama_url = ollama_url
        self.api_endpoint = f"{ollama_url}/api/generate"
        self.ollama_available = self._check_ollama_available()

        if self.ollama_available:
            logger.info("local_model_handler_initialized",
                       model=model,
                       status="✅ Ollama running",
                       url=ollama_url)
        else:
            logger.warning("local_model_handler_initialized",
                          model=model,
                          status="⚠️ Ollama not running - will fallback to cloud",
                          hint="Spusť: docker start voice-assistant-ollama")

    def _check_ollama_available(self) -> bool:
        """Zkontroluj, zda je Ollama server dostupný"""
        try:
            # ✅ OPRAVA: timeout 2.0 → 5.0
            response = httpx.get(f"{self.ollama_url}/api/tags", timeout=5.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                logger.info("ollama_server_available", models_count=len(models))
                return True
            else:
                logger.warning("ollama_server_not_responding", status=response.status_code)
                return False
        except httpx.ConnectError:
            logger.warning("ollama_server_not_running",
                         message="Ollama není spuštěná. Spusť: docker start voice-assistant-ollama")
            return False
        except Exception as e:
            logger.warning("ollama_check_failed", error=str(e))
            return False

    def process(self, text: str) -> str:
        """
        Zpracuje jednoduchý dotaz lokálně pomocí Ollama.
        Pokud Ollama není dostupná, vrátí placeholder pro eskalaci.

        Args:
            text: Text příkazu

        Returns:
            Odpověď z lokálního modelu nebo placeholder
        """
        # Pokud Ollama není dostupná, vrať placeholder (automaticky eskaluje do cloudu)
        if not self.ollama_available:
            logger.info("ollama_not_available_fallback")
            return "[Lokální AI není dostupná - použiji cloud]"

        logger.info("processing_with_local_ollama", text=text[:100], model=self.model)

        try:
            # System prompt pro hlasového asistenta
            prompt = f"""Jsi inteligentní hlasový asistent pro česky mluvícího uživatele.

Pravidla:
- Odpovídej VŽDY v češtině
- Buď stručný: maximálně 2-3 věty
- Odpovídej přirozeně a příjemně
- Pokud nevíš odpověď, řekni to upřímně

Dotaz uživatele: {text}

Odpověď:"""

            # HTTP request na Ollama API
            with httpx.Client(timeout=15.0) as client:
                response = client.post(
                    self.api_endpoint,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 150,  # Max 150 tokenů pro stručnost
                            "top_k": 40,
                            "top_p": 0.9,
                        }
                    }
                )

            if response.status_code == 200:
                result = response.json()
                answer = result.get("response", "").strip()

                # Logování performance
                eval_duration = result.get("eval_duration", 0) / 1e9  # nanosec -> sec
                eval_count = result.get("eval_count", 0)
                tokens_per_sec = eval_count / eval_duration if eval_duration > 0 else 0

                logger.info("local_ollama_success",
                           model=self.model,
                           tokens=eval_count,
                           duration_sec=round(eval_duration, 2),
                           tokens_per_sec=round(tokens_per_sec, 1),
                           response_preview=answer[:80])

                return answer
            else:
                logger.error("ollama_api_error",
                           status=response.status_code,
                           error=response.text[:200])
                return "[Lokální AI vrátila chybu - zkusím cloud]"

        except httpx.ReadTimeout:
            logger.error("ollama_timeout", model=self.model)
            return "[Lokální AI je příliš pomalá - zkusím cloud]"
        except httpx.ConnectError:
            logger.error("ollama_connection_failed")
            self.ollama_available = False  # Označ jako nedostupnou
            return "[Lokální AI přestala běžet - zkusím cloud]"
        except Exception as e:
            logger.error("local_model_error", error=str(e), error_type=type(e).__name__)
            return "[Lokální AI selhala - zkusím cloud]"
