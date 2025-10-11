"""
User Configuration Manager
Načítá a spravuje uživatelskou konfiguraci s validací
"""

import yaml
import os
import structlog
from pathlib import Path
from typing import Dict, Any, Optional, TypeVar, Union

logger = structlog.get_logger()

T = TypeVar('T')


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


class UserConfig:
    """Manager pro uživatelskou konfiguraci s validací"""

    def __init__(self, config_path: str = "config/user_config.yaml"):
        """
        Args:
            config_path: Cesta ke konfiguračnímu souboru
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.validation_errors: list = []
        self._load_config()
        self._validate_config()

    def _load_config(self) -> None:
        """Načti konfiguraci ze souboru"""
        try:
            if not self.config_path.exists():
                logger.warning("config_not_found", path=str(self.config_path))
                self._create_default_config()
                return

            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}

            logger.info("user_config_loaded",
                        user_name=self.config.get('user', {}).get('name', 'Unknown'))

        except Exception as e:
            logger.error("config_load_error", error=str(e))
            raise ConfigValidationError(f"Failed to load config: {e}")

    def _validate_config(self) -> None:
        """Validuj konfiguraci"""
        self.validation_errors = []

        # Validace audio konfigurace
        self._validate_audio_config()

        # Validace model konfigurace
        self._validate_model_config()

        # Validace assistant konfigurace
        self._validate_assistant_config()

        # Validace location konfigurace
        self._validate_location_config()

        # Pokud jsou chyby, zaloguj je
        if self.validation_errors:
            logger.warning("config_validation_warnings",
                          errors=self.validation_errors,
                          count=len(self.validation_errors))

            # Pro development - vypiš do konzole
            print("\n" + "="*60)
            print("⚠️  CONFIGURATION WARNINGS")
            print("="*60)
            for error in self.validation_errors:
                print(f"  • {error}")
            print("="*60 + "\n")

    def _validate_audio_config(self) -> None:
        """Validace audio konfigurace"""
        # Sample rate
        sample_rate = self.get('audio.sample_rate', 16000)
        if not isinstance(sample_rate, int):
            self.validation_errors.append(
                f"audio.sample_rate must be integer, got {type(sample_rate).__name__}"
            )
        elif sample_rate not in [8000, 11025, 16000, 22050, 44100, 48000]:
            self.validation_errors.append(
                f"audio.sample_rate should be one of [8000, 16000, 22050, 44100], got {sample_rate}"
            )

        # Channels
        channels = self.get('audio.channels', 1)
        if not isinstance(channels, int):
            self.validation_errors.append(
                f"audio.channels must be integer, got {type(channels).__name__}"
            )
        elif channels not in [1, 2]:
            self.validation_errors.append(
                f"audio.channels must be 1 (mono) or 2 (stereo), got {channels}"
            )

        # Chunk size
        chunk_size = self.get('audio.chunk_size', 1280)
        if not isinstance(chunk_size, int):
            self.validation_errors.append(
                f"audio.chunk_size must be integer, got {type(chunk_size).__name__}"
            )
        elif chunk_size < 128 or chunk_size > 8192:
            self.validation_errors.append(
                f"audio.chunk_size should be between 128-8192, got {chunk_size}"
            )

        # Gain
        gain = self.get('audio.gain', 6.0)
        if not isinstance(gain, (int, float)):
            self.validation_errors.append(
                f"audio.gain must be number, got {type(gain).__name__}"
            )
        elif gain < 0.0 or gain > 20.0:
            self.validation_errors.append(
                f"audio.gain should be between 0.0-20.0, got {gain}"
            )

        # Wake word threshold
        threshold = self.get('assistant.wake_word_threshold', 0.5)
        if not isinstance(threshold, (int, float)):
            self.validation_errors.append(
                f"assistant.wake_word_threshold must be number, got {type(threshold).__name__}"
            )
        elif threshold < 0.0 or threshold > 1.0:
            self.validation_errors.append(
                f"assistant.wake_word_threshold must be between 0.0-1.0, got {threshold}"
            )

    def _validate_model_config(self) -> None:
        """Validace model konfigurace"""
        # Cloud provider
        provider = self.get('models.cloud.provider', 'openai')
        valid_providers = ['openai', 'anthropic', 'groq']
        if provider not in valid_providers:
            self.validation_errors.append(
                f"models.cloud.provider must be one of {valid_providers}, got '{provider}'"
            )

        # Temperature
        for model_type in ['cloud', 'local']:
            temp = self.get(f'models.{model_type}.temperature', 0.7)
            if not isinstance(temp, (int, float)):
                self.validation_errors.append(
                    f"models.{model_type}.temperature must be number, got {type(temp).__name__}"
                )
            elif temp < 0.0 or temp > 2.0:
                self.validation_errors.append(
                    f"models.{model_type}.temperature should be between 0.0-2.0, got {temp}"
                )

            # Max tokens
            max_tokens = self.get(f'models.{model_type}.max_tokens', 150)
            if not isinstance(max_tokens, int):
                self.validation_errors.append(
                    f"models.{model_type}.max_tokens must be integer, got {type(max_tokens).__name__}"
                )
            elif max_tokens < 10 or max_tokens > 4096:
                self.validation_errors.append(
                    f"models.{model_type}.max_tokens should be between 10-4096, got {max_tokens}"
                )

    def _validate_assistant_config(self) -> None:
        """Validace assistant konfigurace"""
        # Response style
        style = self.get('assistant.response_style', 'stručný')
        valid_styles = ['stručný', 'detailed', 'conversational']
        if style not in valid_styles:
            logger.debug("assistant_response_style_custom", style=style)

        # Max sentences
        max_sentences = self.get('assistant.rules.max_sentences', 3)
        if not isinstance(max_sentences, int):
            self.validation_errors.append(
                f"assistant.rules.max_sentences must be integer, got {type(max_sentences).__name__}"
            )
        elif max_sentences < 1 or max_sentences > 10:
            self.validation_errors.append(
                f"assistant.rules.max_sentences should be between 1-10, got {max_sentences}"
            )

    def _validate_location_config(self) -> None:
        """Validace location konfigurace"""
        auto_detect = self.get('location.auto_detect', True)
        if not isinstance(auto_detect, bool):
            self.validation_errors.append(
                f"location.auto_detect must be boolean, got {type(auto_detect).__name__}"
            )

        # Pokud není auto_detect, zkontroluj manual config
        if not auto_detect:
            manual_city = self.get('location.manual.city')
            if not manual_city:
                self.validation_errors.append(
                    "location.manual.city is required when auto_detect is false"
                )

            manual_timezone = self.get('location.manual.timezone')
            if not manual_timezone:
                self.validation_errors.append(
                    "location.manual.timezone is required when auto_detect is false"
                )

    def _create_default_config(self) -> None:
        """Vytvoř výchozí konfigurační soubor"""
        default_config = {
            'user': {
                'name': 'User',
                'language': 'cs'
            },
            'location': {
                'auto_detect': True,
                'manual': {
                    'city': 'Prague',
                    'region': '',
                    'country': 'Česká republika',
                    'timezone': 'Europe/Prague'
                },
                'fallback': {
                    'city': 'Prague',
                    'country': 'Česká republika',
                    'timezone': 'Europe/Prague'
                }
            },
            'preferences': {
                'temperature_unit': 'celsius',
                'time_format': '24h'
            },
            'assistant': {
                'name': 'Alexa',
                'personality': 'přátelský',
                'response_style': 'stručný',
                'tone': 'casual',
                'wake_word': 'Alexa',
                'wake_word_threshold': 0.5,
                'rules': {
                    'max_sentences': 3,
                    'use_emoji': False,
                    'formality': 'ty'
                }
            },
            'models': {
                'cloud': {
                    'provider': 'openai',
                    'model': 'gpt-4o-mini',
                    'temperature': 0.7,
                    'max_tokens': 150,
                    'streaming': True
                },
                'local': {
                    'provider': 'ollama',
                    'model': 'llama3.2:3b',
                    'temperature': 0.7,
                    'max_tokens': 150,
                    'url': 'http://localhost:11434'
                }
            },
            'routing': {
                'strategy': 'intelligent',
                'use_local_for': ['time_queries', 'date_queries', 'simple_calculations'],
                'use_cloud_for': ['complex_reasoning', 'creative_tasks', 'knowledge_queries'],
                'thresholds': {
                    'local_confidence': 0.8,
                    'max_local_time': 2.0
                }
            },
            'audio': {
                'sample_rate': 16000,
                'channels': 1,
                'chunk_size': 1280,
                'gain': 6.0,
                'wake_word_models': ['alexa'],
                'stt': {
                    'primary': 'groq',
                    'fallback': 'whisper',
                    'whisper_model': 'small',
                    'language': 'cs'
                }
            }
        }

        try:
            # Vytvoř složku config, pokud neexistuje
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False)

            self.config = default_config
            logger.info("default_config_created", path=str(self.config_path))

        except Exception as e:
            logger.error("config_create_error", error=str(e))
            raise ConfigValidationError(f"Failed to create default config: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Získej hodnotu z konfigurace pomocí tečkové notace.

        Args:
            key_path: Cesta ke klíči (např. "user.name")
            default: Výchozí hodnota, pokud klíč neexistuje

        Returns:
            Hodnota z konfigurace nebo default
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default

        # Simple type checking
        if value is not None and default is not None:
            if type(value) != type(default):
                logger.warning(
                    "config_type_mismatch",
                    key=key_path,
                    expected=type(default).__name__,
                    got=type(value).__name__,
                    value=str(value)[:100]
                )
                return default

        return value

    def get_typed(self, key_path: str, default: T, expected_type: type = None) -> T:
        """
        Získej hodnotu s explicitní type checking.

        Args:
            key_path: Cesta ke klíči
            default: Výchozí hodnota
            expected_type: Očekávaný typ (optional)

        Returns:
            Hodnota správného typu nebo default
        """
        value = self.get(key_path, default)

        if expected_type and value is not None:
            if not isinstance(value, expected_type):
                logger.error(
                    "config_type_validation_failed",
                    key=key_path,
                    expected=expected_type.__name__,
                    got=type(value).__name__
                )
                return default

        return value

    def reload(self) -> None:
        """Znovu načti konfiguraci ze souboru"""
        logger.info("reloading_config")
        self._load_config()
        self._validate_config()

    def is_valid(self) -> bool:
        """Check if configuration is valid"""
        return len(self.validation_errors) == 0

    def get_validation_errors(self) -> list:
        """Get list of validation errors"""
        return self.validation_errors.copy()


# Singleton instance
_user_config: Optional[UserConfig] = None


def get_user_config(config_path: str = "config/user_config.yaml") -> UserConfig:
    """
    Získej globální instanci UserConfig.

    Args:
        config_path: Cesta ke konfiguračnímu souboru

    Returns:
        UserConfig instance

    Raises:
        ConfigValidationError: If config cannot be loaded
    """
    global _user_config
    if _user_config is None:
        _user_config = UserConfig(config_path)
    return _user_config
