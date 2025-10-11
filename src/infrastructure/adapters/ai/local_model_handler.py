"""
Lokální AI model handler s Ollama (Llama 3.2 3B)
Vylepšeno: config z UserConfig, lepší error handling
"""

import structlog
import httpx
from typing import Optional
from src.core.ports.i_command_handler import ICommandHandler
from src.core.exceptions import AIError

logger = structlog.get_logger()


class OllamaUnavailableError(AIError):
    """Raised when Ollama server is not available"""
    pass


class LocalModelHandler(ICommandHandler):
    """
    Handler pro zpracování jednoduchých dotazů lokálním LLM (Ollama).

    Automaticky detekuje jestli Ollama běží:
    - Pokud ANO → použije lokální model (rychlé!)
    - Pokud NE → raise exception (caller rozhodne co dělat)
    """

    def __init__(self, model: str = "llama3.2:3b",
                 ollama_url: str = "http://localhost:11434",
                 user_config=None):
        """
        Args:
            model: Ollama model name
            ollama_url: URL Ollama API serveru
            user_config: UserConfig instance pro načítání konfigurace
        """
        self.user_config = user_config

        # Load config
        if user_config:
            self.model = user_config.get('models.local.model', model)
            self.ollama_url = user_config.get('models.local.url', ollama_url)
            self.temperature = user_config.get('models.local.temperature', 0.7)
            self.max_tokens = user_config.get('models.local.max_tokens', 150)
            self.timeout = user_config.get('models.local.timeout', 15.0)
        else:
            self.model = model
            self.ollama_url = ollama_url
            self.temperature = 0.7
            self.max_tokens = 150
            self.timeout = 15.0

        self.api_endpoint = f"{self.ollama_url}/api/generate"
        self.ollama_available = self._check_ollama_available()

        if self.ollama_available:
            logger.info("local_model_handler_initialized",
                       model=self.model,
                       status="✅ Ollama running",
                       url=self.ollama_url)
        else:
            logger.warning("local_model_handler_initialized",
                          model=self.model,
                          status="⚠️ Ollama not running",
                          hint="Spusť: docker start voice-assistant-ollama")

    def _check_ollama_available(self) -> bool:
        """Zkontroluj, zda je Ollama server dostupný"""
        try:
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
        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.warning("ollama_check_failed", error=str(e))
            return False

    def process(self, text: str) -> str:
        """
        Zpracuje jednoduchý dotaz lokálně pomocí Ollama.

        Args:
            text: Text příkazu

        Returns:
            Odpověď z lokálního modelu

        Raises:
            OllamaUnavailableError: Pokud Ollama není dostupná
        """
        # Pokud Ollama není dostupná, raise exception
        if not self.ollama_available:
            logger.warning("ollama_not_available")
            raise OllamaUnavailableError("Ollama server is not running")

        logger.info("processing_with_local_ollama",
                   text=text[:100],
                   model=self.model)

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
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.api_endpoint,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens,
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
                raise AIError(f"Ollama API error: {response.status_code}")

        except httpx.ReadTimeout:
            logger.error("ollama_timeout", model=self.model, timeout=self.timeout)
            raise AIError(f"Ollama timeout after {self.timeout}s")
        except httpx.ConnectError:
            logger.error("ollama_connection_failed")
            self.ollama_available = False  # Označ jako nedostupnou
            raise OllamaUnavailableError("Ollama connection failed")
        except Exception as e:
            logger.error("local_model_error",
                        error=str(e),
                        error_type=type(e).__name__)
            raise AIError(f"Local model processing failed: {e}") from e
