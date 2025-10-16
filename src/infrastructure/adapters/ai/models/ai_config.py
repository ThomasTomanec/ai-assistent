# src/infrastructure/adapters/ai/models/ai_config.py

"""AI Handler Configuration - Enterprise Grade"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AIConfig:
    """Production AI configuration with full feature set."""

    # ========================================
    # Basic Settings
    # ========================================
    user_preference: Optional[str] = None  # 'local_only', 'cloud_only', 'intelligent'

    # ========================================
    # Timeout Settings
    # ========================================
    cloud_timeout: float = 10.0  # Cloud API timeout (seconds)
    local_timeout: float = 30.0  # Local Ollama timeout

    # ========================================
    # Circuit Breaker (per handler)
    # ========================================
    circuit_breaker_enabled: bool = True
    cloud_failure_threshold: int = 3  # Failures before opening circuit
    local_failure_threshold: int = 2  # Failures before opening circuit
    recovery_timeout: float = 60.0  # Seconds before retry (half-open)
    success_threshold: int = 2  # Successes to close circuit

    # ========================================
    # Response Cache
    # ========================================
    cache_enabled: bool = True
    cache_max_size: int = 100  # Max cached responses
    cache_default_ttl: float = 300.0  # Default 5 minutes
    cache_use_smart_ttl: bool = True  # Use smart TTL strategy

    # ========================================
    # Race Mode (parallel cloud + local)
    # ========================================
    race_mode_enabled: bool = False  # Disabled by default (more resource intensive)
    race_mode_threshold: float = 5.0  # Use race if avg latency > 5s
    race_mode_winner_margin: float = 0.5  # Min time diff to declare winner (s)

    # ========================================
    # Retry Settings
    # ========================================
    max_retries: int = 2
    retry_delay: float = 1.0
    retry_backoff: float = 2.0  # Exponential backoff multiplier

    # ========================================
    # Latency Tracking
    # ========================================
    track_latency: bool = True
    latency_window: int = 50  # Track last N requests
    latency_percentiles: list = None  # [50, 90, 95, 99]

    # ========================================
    # Adaptive Routing
    # ========================================
    adaptive_routing: bool = True
    cloud_latency_threshold: float = 3.0  # Switch to local if cloud > 3s
    adaptive_sample_size: int = 10  # Sample size for decision

    # ========================================
    # Monitoring & Observability
    # ========================================
    enable_metrics: bool = True
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR

    def __post_init__(self):
        """Validate and set defaults"""
        if self.latency_percentiles is None:
            self.latency_percentiles = [50, 90, 95, 99]

    def to_dict(self) -> dict:
        """Export as dict"""
        return {
            'user_preference': self.user_preference,
            'cloud_timeout': self.cloud_timeout,
            'local_timeout': self.local_timeout,
            'circuit_breaker_enabled': self.circuit_breaker_enabled,
            'cache_enabled': self.cache_enabled,
            'race_mode_enabled': self.race_mode_enabled,
            'adaptive_routing': self.adaptive_routing,
            'track_latency': self.track_latency
        }
