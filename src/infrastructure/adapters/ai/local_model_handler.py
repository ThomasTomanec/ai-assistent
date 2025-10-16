# src/infrastructure/adapters/ai/local_model_handler.py

"""
Local AI Model Handler (Ollama) - 100% Silent Fallback
Žádné error/debug logy - jen INFO při success
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
    Handler pro zpracování dotazů lokálním LLM (Ollama).
    100% tichý fallback - jen INFO při success.
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
            self.timeout = user_config.get('models.local.timeout', 30)
        else:
            self.model = model
            self.ollama_url = ollama_url
            self.timeout = 30

        self.available = self._check_availability()

        # Tichá inicializace (žádný log)
        if self.available:
            logger.info("local_model_ready", model=self.model)

    def _check_availability(self) -> bool:
        """Check if Ollama is running (completely silent)"""
        try:
            response = httpx.get(f"{self.ollama_url}/api/tags", timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False

    def process(self, text: str) -> str:
        """
        Process command using local Ollama model.

        Args:
            text: User input text

        Returns:
            Model response

        Raises:
            OllamaUnavailableError: If Ollama is not available
            AIError: If processing fails
        """
        if not self.available:
            # Tichý fail
            raise OllamaUnavailableError("Ollama is not available")

        try:
            # Call Ollama API
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": text,
                    "stream": False
                },
                timeout=self.timeout
            )

            # Check response status
            if response.status_code != 200:
                # Tichý fail
                raise AIError(f"Ollama API error: {response.status_code}")

            # Parse response
            data = response.json()
            result = data.get("response", "").strip()

            if not result:
                # Tichý fail
                raise AIError("Local model returned empty response")

            # Success - JEN TADY LOG!
            logger.info("local_model_success",
                        text_length=len(text),
                        response_length=len(result))

            return result

        except httpx.TimeoutException:
            # Tichý fail
            raise AIError(f"Local model timeout after {self.timeout}s")

        except httpx.RequestError as e:
            # Tichý fail
            raise OllamaUnavailableError(f"Cannot connect to Ollama: {e}")

        except AIError:
            # Re-raise bez logu
            raise

        except Exception as e:
            # Tichý fail i pro neočekávané chyby
            raise AIError(f"Local model processing failed: {e}")

    def is_available(self) -> bool:
        """Check if handler is available"""
        return self.available
