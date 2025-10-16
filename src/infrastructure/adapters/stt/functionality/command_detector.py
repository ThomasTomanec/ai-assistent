# src/infrastructure/adapters/stt/functionality/command_detector.py

"""
Command detection functionality for Czech voice assistant.
Detects whether transcribed text is a valid command vs. conversation.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from src.core.config.pattern_config import CommandPatternConfig, get_pattern_config
from src.core.logging.logger import get_logger

logger = get_logger(__name__)


class CommandStatus(Enum):
    """Status detekce příkazu."""
    UNKNOWN = "unknown"  # Ještě nevíme
    VALID_COMMAND = "valid_command"  # Validní příkaz
    INCOMPLETE = "incomplete"  # Neúplný příkaz (čekej na pokračování)
    CONVERSATION = "conversation"  # Konverzace, ne příkaz
    NOISE = "noise"  # Šum/nesmysl


@dataclass
class CommandAnalysis:
    """Výsledek analýzy příkazu."""
    status: CommandStatus
    confidence: float  # 0.0 - 1.0
    score: int
    matched_patterns: Dict[str, List[str]]
    word_count: int
    char_count: int
    has_sentence_ender: bool

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'status': self.status.value,
            'confidence': self.confidence,
            'score': self.score,
            'matched_patterns': self.matched_patterns,
            'word_count': self.word_count,
            'char_count': self.char_count,
            'has_sentence_ender': self.has_sentence_ender
        }


class CommandDetector:
    """
    Sofistikovaná detekce příkazů vs. konverzace.
    Používá konfigurovatelné patterns z YAML.
    """

    def __init__(self, pattern_config: Optional[CommandPatternConfig] = None):
        """
        Args:
            pattern_config: Optional custom pattern config.
                           If None, uses global singleton.
        """
        self.config = pattern_config or get_pattern_config()
        self._command_history: List[str] = []

        logger.debug(
            f"CommandDetector initialized with {len(self.config.command_verbs)} verbs, "
            f"{len(self.config.question_words)} question words"
        )

    def analyze(
            self,
            text: str,
            is_final: bool = False,
            context: Optional[Dict[str, Any]] = None
    ) -> CommandAnalysis:
        """
        Analyzuj text a urči jeho status.

        Args:
            text: Text k analýze
            is_final: Je to finální transcript?
            context: Volitelný kontext (např. previous commands)

        Returns:
            CommandAnalysis s detailními informacemi
        """
        # Edge cases
        if not text or len(text.strip()) < 3:
            return CommandAnalysis(
                status=CommandStatus.NOISE,
                confidence=1.0,
                score=0,
                matched_patterns={},
                word_count=0,
                char_count=0,
                has_sentence_ender=False
            )

        # Normalizuj text
        text_clean = text.strip()
        if not self.config.case_sensitive:
            text_clean = text_clean.lower()

        words = text_clean.split()

        # 1. Custom rules - highest priority
        if text_clean in self.config.custom_rules.always_commands:
            return self._create_analysis(
                CommandStatus.VALID_COMMAND,
                text_clean,
                words,
                score=100,
                confidence=1.0
            )

        if text_clean in self.config.custom_rules.never_commands:
            return self._create_analysis(
                CommandStatus.CONVERSATION,
                text_clean,
                words,
                score=-100,
                confidence=1.0
            )

        # 2. Length checks
        if len(words) > self.config.scoring.max_command_words:
            return self._create_analysis(
                CommandStatus.CONVERSATION,
                text_clean,
                words,
                score=-50,
                confidence=0.9
            )

        if len(text_clean) < self.config.scoring.min_command_length:
            return self._create_analysis(
                CommandStatus.UNKNOWN,
                text_clean,
                words,
                score=0,
                confidence=0.0
            )

        # 3. Pattern matching & scoring
        score = 0
        matched_patterns = {
            'command_verbs': [],
            'question_words': [],
            'conversation_indicators': []
        }

        first_word = words[0]

        # Command verb na začátku
        for verb in self.config.command_verbs:
            if first_word.startswith(verb):
                score += self.config.scoring.command_verb_start
                matched_patterns['command_verbs'].append(verb)
                break

        # Question word na začátku
        if first_word in self.config.question_words:
            score += self.config.scoring.question_word_start
            matched_patterns['question_words'].append(first_word)

        # Command verb kdekoli
        for verb in self.config.command_verbs:
            if verb in text_clean and verb not in matched_patterns['command_verbs']:
                score += self.config.scoring.command_verb_anywhere
                matched_patterns['command_verbs'].append(verb)

        # Question word kdekoli
        for qw in self.config.question_words:
            if qw in text_clean and qw not in matched_patterns['question_words']:
                score += self.config.scoring.question_word_anywhere
                matched_patterns['question_words'].append(qw)

        # Conversation indicators (negative score)
        for ci in self.config.conversation_indicators:
            if ci in text_clean:
                score += self.config.scoring.conversation_penalty
                matched_patterns['conversation_indicators'].append(ci)

        # Sentence ender check
        has_ender = text_clean[-1] in self.config.sentence_enders

        # 4. Determine status based on score
        status = self._determine_status(score, has_ender, is_final, len(words))

        # 5. Calculate confidence
        confidence = self._calculate_confidence(score, matched_patterns, len(words))

        return CommandAnalysis(
            status=status,
            confidence=confidence,
            score=score,
            matched_patterns=matched_patterns,
            word_count=len(words),
            char_count=len(text_clean),
            has_sentence_ender=has_ender
        )

    def _determine_status(
            self,
            score: int,
            has_ender: bool,
            is_final: bool,
            word_count: int
    ) -> CommandStatus:
        """Urči status podle score a dalších faktorů."""

        if score >= self.config.scoring.command_threshold:
            # Pravděpodobně příkaz
            if has_ender or is_final:
                return CommandStatus.VALID_COMMAND
            else:
                return CommandStatus.INCOMPLETE

        elif score <= self.config.scoring.conversation_threshold:
            # Pravděpodobně konverzace
            return CommandStatus.CONVERSATION

        else:
            # Nevíme - další heuristiky
            if has_ender and word_count > self.config.scoring.conversation_word_threshold:
                # Dlouhý text bez strong indicators = konverzace
                return CommandStatus.CONVERSATION

            return CommandStatus.UNKNOWN

    def _calculate_confidence(
            self,
            score: int,
            matched_patterns: Dict[str, List[str]],
            word_count: int
    ) -> float:
        """Vypočítej confidence (0.0 - 1.0)."""
        # Base confidence from score
        if score >= 5:
            base = 0.95
        elif score >= 3:
            base = 0.80
        elif score >= 1:
            base = 0.60
        elif score == 0:
            base = 0.30
        elif score >= -1:
            base = 0.20
        else:
            base = 0.10

        # Boost if multiple patterns matched
        pattern_count = sum(len(p) for p in matched_patterns.values())
        if pattern_count >= 3:
            base = min(1.0, base + 0.10)

        # Penalize very short/long texts
        if word_count < 2:
            base *= 0.7
        elif word_count > 30:
            base *= 0.8

        return round(base, 2)

    def _create_analysis(
            self,
            status: CommandStatus,
            text: str,
            words: List[str],
            score: int,
            confidence: float
    ) -> CommandAnalysis:
        """Helper pro vytvoření CommandAnalysis."""
        return CommandAnalysis(
            status=status,
            confidence=confidence,
            score=score,
            matched_patterns={},
            word_count=len(words),
            char_count=len(text),
            has_sentence_ender=text[-1] in self.config.sentence_enders if text else False
        )

    def should_continue_recording(
            self,
            analysis: CommandAnalysis,
            silence_duration: float
    ) -> bool:
        """
        Rozhodnutí jestli pokračovat v nahrávání.

        Args:
            analysis: Výsledek analýzy příkazu
            silence_duration: Jak dlouho je ticho (sekundy)

        Returns:
            True pokud pokračovat, False pokud ukončit
        """
        # Timeouty podle statusu
        timeouts = {
            CommandStatus.VALID_COMMAND: 0.8,  # Rychlé ukončení
            CommandStatus.CONVERSATION: 0.3,  # Velmi rychlé
            CommandStatus.INCOMPLETE: 1.5,  # Normální
            CommandStatus.UNKNOWN: 2.0,  # Čekej déle
            CommandStatus.NOISE: 0.5  # Rychlé ukončení
        }

        timeout = timeouts.get(analysis.status, 1.5)

        # S nízkou confidence čekej déle
        if analysis.confidence < 0.5:
            timeout *= 1.3

        return silence_duration < timeout

    def add_to_history(self, text: str) -> None:
        """Přidej příkaz do historie (pro context-aware detection)."""
        self._command_history.append(text)
        # Keep only last 10
        if len(self._command_history) > 10:
            self._command_history.pop(0)

    def get_debug_info(self, text: str) -> Dict[str, Any]:
        """
        Debug informace o analýze (pro logging/testing).

        Returns:
            Dictionary s debug info
        """
        analysis = self.analyze(text)

        return {
            'text': text,
            'analysis': analysis.to_dict(),
            'config_summary': {
                'command_verbs_count': len(self.config.command_verbs),
                'question_words_count': len(self.config.question_words),
                'language': self.config.language
            }
        }
