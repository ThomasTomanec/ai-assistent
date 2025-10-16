# src/infrastructure/adapters/stt/streaming_stt_adapter.py

from src.infrastructure.adapters.stt.functionality import (
    CommandDetector,
    CommandStatus,
    CommandAnalysis
)
from src.core.config.pattern_config import get_pattern_config


class StreamingSTTAdapter(ISTTEngine):

    def __init__(self, config: StreamingConfig):
        # ... existing code ...

        # Initialize command detector
        pattern_config = get_pattern_config()
        self.command_detector = CommandDetector(pattern_config)

    async def _on_transcript(self, result, **kwargs):
        """Transcript received."""
        sentence = result.channel.alternatives[0].transcript

        if not sentence:
            return

        # Analyze command
        analysis = self.command_detector.analyze(
            sentence,
            is_final=result.is_final
        )

        # Log with confidence
        logger.info(
            f"📝 {sentence} "
            f"[{analysis.status.value}, confidence={analysis.confidence}]"
        )

        # Callback
        if self._on_command_status:
            self._on_command_status(analysis)
