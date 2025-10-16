# src/infrastructure/adapters/audio/vad/models/__init__.py

"""VAD models - data classes for configuration and metrics."""

from .recording_config import RecordingConfig
from .recording_metrics import RecordingMetrics

__all__ = [
    'RecordingConfig',
    'RecordingMetrics'
]
