# tests/infrastructure/adapters/stt/functionality/test_command_detector.py

import pytest
from src.infrastructure.adapters.stt.functionality import (
    CommandDetector,
    CommandStatus
)
from src.core.config.pattern_config import CommandPatternConfig


class TestCommandDetector:

    @pytest.fixture
    def detector(self):
        # Load test config
        config = CommandPatternConfig("config/command_patterns.test.yaml")
        return CommandDetector(config)

    def test_valid_command(self, detector):
        """Test validní příkaz."""
        analysis = detector.analyze("zapni světla v obýváku")

        assert analysis.status == CommandStatus.VALID_COMMAND
        assert analysis.confidence > 0.7
        assert 'zapni' in analysis.matched_patterns['command_verbs']

    def test_question(self, detector):
        """Test otázka."""
        analysis = detector.analyze("kolik je hodin?")

        assert analysis.status == CommandStatus.VALID_COMMAND
        assert 'kolik' in analysis.matched_patterns['question_words']

    def test_conversation(self, detector):
        """Test konverzace."""
        analysis = detector.analyze("myslím že asi nevím co dneska budeme dělat")

        assert analysis.status == CommandStatus.CONVERSATION
        assert analysis.confidence > 0.7

    def test_incomplete_command(self, detector):
        """Test neúplný příkaz."""
        analysis = detector.analyze("zapni světla", is_final=False)

        assert analysis.status == CommandStatus.INCOMPLETE

    def test_noise(self, detector):
        """Test šum."""
        analysis = detector.analyze("eh um")

        assert analysis.status in [CommandStatus.NOISE, CommandStatus.UNKNOWN]
