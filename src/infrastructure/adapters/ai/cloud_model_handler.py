"""
Cloud AI model handler with streaming callback support
Vylepšeno: visual streaming, retry logic, lazy internet check
"""

import structlog
import os
import httpx
import time
from datetime import datetime, timedelta
from typing import Optional, Callable
from openai import OpenAI
from src.core.ports.i_command_handler import ICommandHandler
from src.application.services.context_builder import ContextBuilder
from src.core.exceptions import AIError

logger = structlog.get_logger()


class CloudProviderUnavailableError(AIError):
    """Raised when cloud provider is not available"""
    pass


class CloudModelHandler(ICommandHandler):
    """Handler pro komunikaci s cloudovým AI API"""

    def __init__(self, context_builder: ContextBuilder, api_key: str = None,
                 provider: str = "openai", streaming: bool = True,
                 user_config=None, response_callback: Callable = None):
        """
        Args:
            context_builder: Service pro sestavování kontextu
            api_key: API klíč pro cloudovou službu
            provider: Poskytovatel ('openai', 'anthropic', atd.)
            streaming: Použít streaming pro rychlejší odpovědi
            user_config: UserConfig instance pro načítání konfigurace
            response_callback: Callback pro streaming chunks (chunk: str, is_final: bool)
        """
        self.context_builder = context_builder
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.provider = provider
        self.streaming = streaming
        self.user_config = user_config
        self.response_callback = response_callback

        # Load config values
        self._load_config()

        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)

        # Internet check (lazy)
        self._internet_checked = False
        self._internet_cache_time = None
        self.internet_available = None

        logger.info("cloud_model_handler_initialized",
                   provider=provider,
                   streaming=streaming,
                   model=self.model)

    def set_response_callback(self, callback: Callable):
        """Set callback for streaming response chunks"""
        self.response_callback = callback

    def _load_config(self) -> None:
        """Load configuration from UserConfig"""
        if self.user_config:
            self.model = self.user_config.get('models.cloud.model', 'gpt-4o-mini')
            self.temperature = self.user_config.get('models.cloud.temperature', 0.7)
            self.max_tokens = self.user_config.get('models.cloud.max_tokens', 150)
            self.internet_check_timeout = self.user_config.get('models.cloud.internet_check_timeout', 3.0)
            self.internet_cache_duration = self.user_config.get('models.cloud.internet_cache_duration', 60)
            self.max_retries = self.user_config.get('models.cloud.max_retries', 3)
        else:
            # Fallback values
            self.model = 'gpt-4o-mini'
            self.temperature = 0.7
            self.max_tokens = 150
            self.internet_check_timeout = 3.0
            self.internet_cache_duration = 60
            self.max_retries = 3

    def _check_internet(self) -> bool:
        """
        Zkontroluj připojení k internetu s caching (60s).

        Returns:
            True pokud je internet dostupný, False jinak
        """
        # Check cache
        if self._internet_cache_time:
            age = (datetime.now() - self._internet_cache_time).total_seconds()
            if age < self.internet_cache_duration:
                logger.debug("internet_check_cache_hit", available=self.internet_available)
                return self.internet_available

        # Perform check
        try:
            httpx.get("https://api.openai.com", timeout=self.internet_check_timeout)
            self.internet_available = True
            logger.debug("internet_check_success")
        except (httpx.RequestError, httpx.TimeoutException) as e:
            self.internet_available = False
            logger.warning("internet_check_failed", error=str(e))

        # Update cache
        self._internet_cache_time = datetime.now()
        return self.internet_available

    def process(self, text: str) -> str:
        """
        Zpracuje dotaz pomocí cloudového AI.

        Args:
            text: Text příkazu

        Returns:
            Odpověď z cloudového modelu

        Raises:
            CloudProviderUnavailableError: Pokud cloud není dostupný
        """
        # Check internet
        if not self._check_internet():
            logger.warning("cloud_offline")
            raise CloudProviderUnavailableError("Internet connection not available")

        logger.info("processing_with_cloud_model",
                   text=text[:100],
                   streaming=self.streaming,
                   model=self.model)

        try:
            if self.provider == "openai":
                if self.streaming:
                    return self._process_openai_streaming(text)
                else:
                    return self._process_openai(text)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except CloudProviderUnavailableError:
            raise  # Re-raise to be handled by caller
        except Exception as e:
            logger.error("cloud_model_error", error=str(e), error_type=type(e).__name__)
            raise AIError(f"Cloud AI processing failed: {e}") from e

    def _process_with_retry(self, func, max_retries: int = None):
        """
        Execute function with exponential backoff retry.

        Args:
            func: Function to execute
            max_retries: Max retry attempts (default from config)

        Returns:
            Function result
        """
        if max_retries is None:
            max_retries = self.max_retries

        last_error = None

        for attempt in range(max_retries):
            try:
                return func()
            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_error = e

                if attempt == max_retries - 1:
                    raise

                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(
                    "cloud_api_retry",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    wait_seconds=wait_time,
                    error=str(e)
                )
                time.sleep(wait_time)

        raise last_error

    def _process_openai_streaming(self, text: str) -> str:
        """Zpracování přes OpenAI API se streamingem a retry logikou"""

        def _make_request():
            # Získej system prompt z context builderu
            system_prompt = self.context_builder.build_system_prompt()

            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
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

                    # Call streaming callback for visual feedback
                    if self.response_callback:
                        self.response_callback(content, is_final=False)

            # Final callback
            if self.response_callback:
                self.response_callback("", is_final=True)

            logger.debug("streaming_complete", response_length=len(full_response))
            return full_response.strip()

        try:
            return self._process_with_retry(_make_request)
        except Exception as e:
            logger.error("openai_streaming_error", error=str(e))
            raise AIError(f"OpenAI streaming failed: {e}") from e

    def _process_openai(self, text: str) -> str:
        """Zpracování přes OpenAI API bez streamingu s retry logikou"""

        def _make_request():
            system_prompt = self.context_builder.build_system_prompt()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            answer = response.choices[0].message.content.strip()
            logger.debug("cloud_model_response", response_length=len(answer))
            return answer

        try:
            return self._process_with_retry(_make_request)
        except Exception as e:
            logger.error("openai_api_error", error=str(e))
            raise AIError(f"OpenAI API failed: {e}") from e
