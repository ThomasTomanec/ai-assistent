# src/infrastructure/adapters/audio/vad/functionality/metrics_tracker.py

"""Metrics tracking for recording."""

import time
import numpy as np
from datetime import datetime
from typing import List

from ..models import RecordingMetrics


class MetricsTracker:
    """
    Sleduje metriky během nahrávání.
    Poskytuje detailní statistiky o kvalitě a výkonu nahrávání.
    """

    def __init__(self):
        """Initialize metrics tracker."""
        self.metrics = RecordingMetrics()
        self.start_time = time.perf_counter()
        self.volumes: List[float] = []

    def update_frame(
            self,
            is_speech: bool,
            volume: float,
            proximity_ok: bool,
            quality_ok: bool
    ) -> None:
        """
        Update metrics for single frame.

        Args:
            is_speech: VAD detected speech
            volume: Frame volume (0.0-1.0)
            proximity_ok: Passed proximity check
            quality_ok: Passed quality validation
        """
        self.metrics.total_frames += 1

        # Speech/silence tracking
        if is_speech:
            self.metrics.speech_frames += 1
        else:
            self.metrics.silence_frames += 1

        # Rejection tracking
        if not proximity_ok:
            self.metrics.proximity_rejected_frames += 1

        if not quality_ok:
            self.metrics.quality_rejected_frames += 1

        # Volume tracking
        self.volumes.append(volume)
        self.metrics.peak_volume = max(self.metrics.peak_volume, volume)
        self.metrics.min_volume = min(self.metrics.min_volume, volume)

        # Quality indicators
        if volume >= 0.95:
            self.metrics.clipping_detected = True

        if volume < 0.001:
            self.metrics.too_quiet = True

    def set_background_noise(self, noise_level: float) -> None:
        """
        Set background noise level.

        Args:
            noise_level: Background noise level
        """
        self.metrics.background_noise = noise_level

    def set_sample_count(self, count: int) -> None:
        """
        Set total sample count.

        Args:
            count: Total number of samples
        """
        self.metrics.total_samples = count

    def finalize(self, stop_reason: str = "unknown") -> RecordingMetrics:
        """
        Finalize metrics and return.

        Args:
            stop_reason: Reason for stopping ("silence", "max_duration", "error")

        Returns:
            Finalized RecordingMetrics
        """
        # Set end time
        self.metrics.end_time = datetime.now()
        self.metrics.stop_reason = stop_reason

        # Calculate volume statistics
        if self.volumes:
            self.metrics.avg_volume = float(np.mean(self.volumes))
        else:
            self.metrics.avg_volume = 0.0

        # Calculate processing time
        processing_time = time.perf_counter() - self.start_time
        self.metrics.processing_time_ms = processing_time * 1000

        return self.metrics

    def get_current_metrics(self) -> RecordingMetrics:
        """
        Get current metrics snapshot without finalizing.

        Returns:
            Current RecordingMetrics (not finalized)
        """
        return self.metrics
