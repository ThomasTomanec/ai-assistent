# src/infrastructure/adapters/ai/models/ai_metrics.py

"""AI Handler Metrics - Production Grade"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
import numpy as np


@dataclass
class AIRequestMetrics:
    """Single request metrics"""
    handler: str  # "cloud" or "local"
    success: bool
    response_length: int = 0
    latency_ms: float = 0.0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    fallback_used: bool = False
    from_cache: bool = False
    circuit_open: bool = False
    race_winner: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> dict:
        """Export as dict"""
        return {
            'handler': self.handler,
            'success': self.success,
            'response_length': self.response_length,
            'latency_ms': round(self.latency_ms, 2),
            'fallback_used': self.fallback_used,
            'from_cache': self.from_cache,
            'circuit_open': self.circuit_open,
            'race_winner': self.race_winner,
            'retry_count': self.retry_count,
            'error': self.error
        }


@dataclass
class AIStatistics:
    """Aggregate AI handler statistics"""

    # Counters
    total_requests: int = 0
    cloud_requests: int = 0
    local_requests: int = 0
    cache_hits: int = 0
    failures: int = 0
    fallbacks: int = 0
    timeouts: int = 0

    # Latency tracking
    cloud_latencies: List[float] = field(default_factory=list)
    local_latencies: List[float] = field(default_factory=list)

    # Circuit breaker
    cloud_circuit_trips: int = 0
    local_circuit_trips: int = 0
    current_cloud_state: str = "closed"
    current_local_state: str = "closed"

    # Race mode
    race_mode_used: int = 0
    cloud_wins: int = 0
    local_wins: int = 0

    def add_latency(self, handler: str, latency: float, window: int = 50):
        """Add latency sample (keep last N)"""
        if handler == "cloud":
            self.cloud_latencies.append(latency)
            if len(self.cloud_latencies) > window:
                self.cloud_latencies.pop(0)
        else:
            self.local_latencies.append(latency)
            if len(self.local_latencies) > window:
                self.local_latencies.pop(0)

    def get_percentile(self, handler: str, percentile: int) -> float:
        """Get latency percentile"""
        latencies = self.cloud_latencies if handler == "cloud" else self.local_latencies
        if not latencies:
            return 0.0
        return float(np.percentile(latencies, percentile))

    def get_avg_latency(self, handler: str) -> float:
        """Get average latency"""
        latencies = self.cloud_latencies if handler == "cloud" else self.local_latencies
        if not latencies:
            return 0.0
        return float(np.mean(latencies))

    def to_dict(self) -> dict:
        """Export as dict"""
        total = max(self.total_requests, 1)

        return {
            # Counters
            'total_requests': self.total_requests,
            'cloud_requests': self.cloud_requests,
            'local_requests': self.local_requests,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': round(self.cache_hits / total * 100, 1),
            'failures': self.failures,
            'failure_rate': round(self.failures / total * 100, 1),
            'fallbacks': self.fallbacks,
            'fallback_rate': round(self.fallbacks / total * 100, 1),
            'timeouts': self.timeouts,

            # Latency
            'cloud_avg_latency_ms': round(self.get_avg_latency('cloud'), 2),
            'cloud_p95_latency_ms': round(self.get_percentile('cloud', 95), 2),
            'cloud_p99_latency_ms': round(self.get_percentile('cloud', 99), 2),
            'local_avg_latency_ms': round(self.get_avg_latency('local'), 2),
            'local_p95_latency_ms': round(self.get_percentile('local', 95), 2),

            # Circuit breaker
            'cloud_circuit_trips': self.cloud_circuit_trips,
            'local_circuit_trips': self.local_circuit_trips,
            'current_cloud_state': self.current_cloud_state,
            'current_local_state': self.current_local_state,

            # Race mode
            'race_mode_used': self.race_mode_used,
            'cloud_wins': self.cloud_wins,
            'local_wins': self.local_wins
        }
