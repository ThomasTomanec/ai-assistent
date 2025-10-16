# src/infrastructure/adapters/ai/functionality/latency_tracker.py

"""Latency Tracker with Percentiles"""

from collections import deque
from typing import List, Dict
import numpy as np
import structlog

logger = structlog.get_logger()


class LatencyTracker:
    """
    Track latency with sliding window and percentiles.
    """

    def __init__(self, window_size: int = 50, enabled: bool = True):
        """
        Args:
            window_size: Number of samples to keep
            enabled: Enable/disable tracking
        """
        self.window_size = window_size
        self.enabled = enabled
        self.latencies: deque = deque(maxlen=window_size)

        logger.debug("latency_tracker_initialized", window_size=window_size)

    def record(self, latency_ms: float) -> None:
        """Record latency sample"""
        if not self.enabled:
            return

        self.latencies.append(latency_ms)

    def get_average(self) -> float:
        """Get average latency"""
        if not self.latencies:
            return 0.0
        return float(np.mean(self.latencies))

    def get_percentile(self, percentile: int) -> float:
        """Get latency percentile (50, 90, 95, 99)"""
        if not self.latencies:
            return 0.0
        return float(np.percentile(list(self.latencies), percentile))

    def get_percentiles(self, percentiles: List[int] = None) -> Dict[str, float]:
        """Get multiple percentiles"""
        if percentiles is None:
            percentiles = [50, 90, 95, 99]

        return {
            f'p{p}': round(self.get_percentile(p), 2)
            for p in percentiles
        }

    def get_min(self) -> float:
        """Get minimum latency"""
        if not self.latencies:
            return 0.0
        return float(min(self.latencies))

    def get_max(self) -> float:
        """Get maximum latency"""
        if not self.latencies:
            return 0.0
        return float(max(self.latencies))

    def is_slow(self, threshold: float) -> bool:
        """Check if average latency exceeds threshold"""
        return self.get_average() > threshold

    def get_stats(self) -> Dict:
        """Get comprehensive statistics"""
        if not self.latencies:
            return {
                'count': 0,
                'avg': 0.0,
                'min': 0.0,
                'max': 0.0,
                **{f'p{p}': 0.0 for p in [50, 90, 95, 99]}
            }

        return {
            'count': len(self.latencies),
            'avg': round(self.get_average(), 2),
            'min': round(self.get_min(), 2),
            'max': round(self.get_max(), 2),
            **self.get_percentiles()
        }

    def reset(self) -> None:
        """Clear all samples"""
        self.latencies.clear()
        logger.debug("latency_tracker_reset")
