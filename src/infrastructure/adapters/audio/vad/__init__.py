# src/infrastructure/adapters/audio/vad/__init__.py

"""
VAD (Voice Activity Detection) module.

Production-ready voice activity detection with:
- Proximity detection (rejects distant TV/people)
- Audio quality validation
- Efficient buffer management
- Comprehensive metrics tracking

Usage:
    from src.infrastructure.adapters.audio.vad import VADRecorder, RecordingConfig

    # Create config
    config = RecordingConfig(
        max_duration=10.0,
        proximity_enabled=True,
        vad_aggressiveness=2
    )

    # Create recorder
    recorder = VADRecorder(audio_input, config=config)

    # Calibrate (once at startup)
    await recorder.calibrate_background(duration=2.0)

    # Record with metrics
    audio, metrics = await recorder.record_until_silence()

    print(f"Quality: {metrics.quality_score:.0%}")
"""

from .vad_recorder import VADRecorder
from .models import RecordingConfig, RecordingMetrics

__all__ = [
    'VADRecorder',
    'RecordingConfig',
    'RecordingMetrics'
]

__version__ = '1.0.0'
