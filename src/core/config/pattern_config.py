# src/core/config/pattern_config.py

from typing import Set, List, Dict, Any
from pathlib import Path
import yaml
from dataclasses import dataclass

from src.core.exceptions import InvalidConfigError
from src.core.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ScoringWeights:
    """Váhy pro scoring."""
    command_verb_start: int
    question_word_start: int
    command_verb_anywhere: int
    question_word_anywhere: int
    conversation_penalty: int
    command_threshold: int
    conversation_threshold: int
    min_command_length: int
    max_command_words: int
    conversation_word_threshold: int


@dataclass
class CustomRules:
    """Custom pravidla pro detekci."""
    always_commands: Set[str]
    never_commands: Set[str]


class CommandPatternConfig:
    """
    Konfigurace pro detekci command patterns.
    Načítá patterns z YAML souboru.
    """

    def __init__(self, config_path: str = "config/command_patterns.yaml"):
        self.config_path = Path(config_path)
        self._load_config()

    def _load_config(self) -> None:
        """Načte konfiguraci ze souboru."""
        if not self.config_path.exists():
            raise InvalidConfigError(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Parse patterns
            patterns = config.get('patterns', {})
            self.command_verbs = set(patterns.get('command_verbs', []))
            self.question_words = set(patterns.get('question_words', []))
            self.conversation_indicators = set(patterns.get('conversation_indicators', []))
            self.sentence_enders = set(patterns.get('sentence_enders', []))

            # Parse scoring
            scoring = config.get('scoring', {})
            self.scoring = ScoringWeights(
                command_verb_start=scoring.get('command_verb_start', 3),
                question_word_start=scoring.get('question_word_start', 3),
                command_verb_anywhere=scoring.get('command_verb_anywhere', 2),
                question_word_anywhere=scoring.get('question_word_anywhere', 2),
                conversation_penalty=scoring.get('conversation_penalty', -2),
                command_threshold=scoring.get('command_threshold', 3),
                conversation_threshold=scoring.get('conversation_threshold', -1),
                min_command_length=scoring.get('min_command_length', 5),
                max_command_words=scoring.get('max_command_words', 50),
                conversation_word_threshold=scoring.get('conversation_word_threshold', 8)
            )

            # Parse custom rules
            custom = config.get('custom_rules', {})
            self.custom_rules = CustomRules(
                always_commands=set(custom.get('always_commands', [])),
                never_commands=set(custom.get('never_commands', []))
            )

            # Settings
            self.language = config.get('language', 'cs')
            self.case_sensitive = config.get('case_sensitive', False)

            logger.info(f"✅ Loaded command patterns config: {len(self.command_verbs)} verbs, "
                        f"{len(self.question_words)} question words")

        except yaml.YAMLError as e:
            raise InvalidConfigError(f"Invalid YAML in config: {e}")
        except Exception as e:
            raise InvalidConfigError(f"Failed to load config: {e}")

    def reload(self) -> None:
        """Znovu načte konfiguraci (hot reload)."""
        logger.info("Reloading command patterns config...")
        self._load_config()

    def add_command_verb(self, verb: str) -> None:
        """Dynamicky přidá command verb (pro runtime customization)."""
        self.command_verbs.add(verb.lower() if not self.case_sensitive else verb)
        logger.debug(f"Added command verb: {verb}")

    def add_custom_command(self, phrase: str) -> None:
        """Přidá custom příkaz do always_commands."""
        self.custom_rules.always_commands.add(
            phrase.lower() if not self.case_sensitive else phrase
        )
        logger.debug(f"Added custom command: {phrase}")

    def to_dict(self) -> Dict[str, Any]:
        """Export config jako dictionary (pro debugging)."""
        return {
            'patterns': {
                'command_verbs': list(self.command_verbs),
                'question_words': list(self.question_words),
                'conversation_indicators': list(self.conversation_indicators),
                'sentence_enders': list(self.sentence_enders)
            },
            'scoring': {
                'command_verb_start': self.scoring.command_verb_start,
                'question_word_start': self.scoring.question_word_start,
                'command_verb_anywhere': self.scoring.command_verb_anywhere,
                'question_word_anywhere': self.scoring.question_word_anywhere,
                'conversation_penalty': self.scoring.conversation_penalty,
                'command_threshold': self.scoring.command_threshold,
                'conversation_threshold': self.scoring.conversation_threshold,
            },
            'custom_rules': {
                'always_commands': list(self.custom_rules.always_commands),
                'never_commands': list(self.custom_rules.never_commands)
            },
            'language': self.language,
            'case_sensitive': self.case_sensitive
        }


# Singleton instance
_pattern_config: Optional[CommandPatternConfig] = None


def get_pattern_config(config_path: str = "config/command_patterns.yaml") -> CommandPatternConfig:
    """Get singleton instance of pattern config."""
    global _pattern_config
    if _pattern_config is None:
        _pattern_config = CommandPatternConfig(config_path)
    return _pattern_config
