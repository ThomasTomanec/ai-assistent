"""
User Configuration Manager
Načítá a spravuje uživatelskou konfiguraci
"""

import yaml
import os
import structlog
from pathlib import Path
from typing import Dict, Any, Optional

logger = structlog.get_logger()


class UserConfig:
    """Manager pro uživatelskou konfiguraci"""

    def __init__(self, config_path: str = "config/user_config.yaml"):
        """
        Args:
            config_path: Cesta ke konfiguračnímu souboru
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._load_config()

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
            self.config = {}

    def _create_default_config(self) -> None:
        """Vytvoř výchozí konfigurační soubor"""
        default_config = {
            'user': {
                'name': 'User',
                'language': 'cs'
            },
            'location': {
                'city': 'Unknown',
                'timezone': 'Europe/Prague',
                'country': 'Česká republika'
            },
            'preferences': {
                'temperature_unit': 'celsius',
                'time_format': '24h'
            },
            'assistant': {
                'personality': 'přátelský',
                'response_style': 'stručný'
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

        return value

    def reload(self) -> None:
        """Znovu načti konfiguraci ze souboru"""
        self._load_config()


# Singleton instance
_user_config: Optional[UserConfig] = None


def get_user_config(config_path: str = "config/user_config.yaml") -> UserConfig:
    """
    Získej globální instanci UserConfig.

    Args:
        config_path: Cesta ke konfiguračnímu souboru

    Returns:
        UserConfig instance
    """
    global _user_config
    if _user_config is None:
        _user_config = UserConfig(config_path)
    return _user_config
