# src/infrastructure/adapters/ai/functionality/circuit_breaker.py

"""Circuit Breaker Pattern - Production Implementation"""

import time
from datetime import datetime
import structlog

from ..models import CircuitState, CircuitMetrics

logger = structlog.get_logger()


class CircuitBreaker:
    """
    Production-grade circuit breaker implementation.

    States:
    - CLOSED: Normal operation, all requests pass
    - OPEN: Failing, reject all requests immediately
    - HALF_OPEN: Testing recovery, allow one test request
    """

    def __init__(
            self,
            name: str,
            failure_threshold: int = 3,
            recovery_timeout: float = 60.0,
            success_threshold: int = 2,
            enabled: bool = True
    ):
        """
        Args:
            name: Circuit name (e.g. "cloud", "local")
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            success_threshold: Successes needed to close from half-open
            enabled: Enable/disable circuit breaker
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.enabled = enabled

        self.metrics = CircuitMetrics(state=CircuitState.CLOSED)

        logger.info(
            "circuit_breaker_initialized",
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            enabled=enabled
        )

    def allow_request(self) -> bool:
        """
        Check if request should be allowed.

        Returns:
            True if request should proceed, False if rejected
        """
        if not self.enabled:
            return True

        # CLOSED: Allow all requests
        if self.metrics.state == CircuitState.CLOSED:
            return True

        # OPEN: Check if recovery timeout elapsed
        if self.metrics.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                logger.info("circuit_attempting_recovery", name=self.name)
                self._transition_to_half_open()
                return True
            return False

        # HALF_OPEN: Allow one test request at a time
        if self.metrics.state == CircuitState.HALF_OPEN:
            return True

        return False

    def record_success(self) -> None:
        """Record successful request"""
        if not self.enabled:
            return

        self.metrics.success_count += 1
        self.metrics.last_success_time = datetime.now()

        # CLOSED: Reset failure count
        if self.metrics.state == CircuitState.CLOSED:
            self.metrics.failure_count = 0

        # HALF_OPEN: Check if should close
        elif self.metrics.state == CircuitState.HALF_OPEN:
            if self.metrics.success_count >= self.success_threshold:
                logger.info(
                    "circuit_closing",
                    name=self.name,
                    success_count=self.metrics.success_count
                )
                self._transition_to_closed()

    def record_failure(self) -> None:
        """Record failed request"""
        if not self.enabled:
            return

        self.metrics.failure_count += 1
        self.metrics.last_failure_time = datetime.now()

        # CLOSED: Check if should open
        if self.metrics.state == CircuitState.CLOSED:
            if self.metrics.failure_count >= self.failure_threshold:
                logger.warning(
                    "circuit_opening",
                    name=self.name,
                    failure_count=self.metrics.failure_count,
                    threshold=self.failure_threshold
                )
                self._transition_to_open()

        # HALF_OPEN: Reopen immediately on any failure
        elif self.metrics.state == CircuitState.HALF_OPEN:
            logger.warning(
                "circuit_reopening",
                name=self.name,
                reason="failure_during_recovery"
            )
            self._transition_to_open()

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if not self.metrics.opened_at:
            return True

        elapsed = (datetime.now() - self.metrics.opened_at).total_seconds()
        return elapsed >= self.recovery_timeout

    def _transition_to_open(self) -> None:
        """Transition to OPEN state"""
        self.metrics.state = CircuitState.OPEN
        self.metrics.opened_at = datetime.now()
        self.metrics.total_trips += 1
        self.metrics.success_count = 0

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state"""
        self.metrics.state = CircuitState.HALF_OPEN
        self.metrics.success_count = 0
        self.metrics.failure_count = 0

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state"""
        self.metrics.state = CircuitState.CLOSED
        self.metrics.failure_count = 0
        self.metrics.success_count = 0
        self.metrics.opened_at = None

    def reset(self) -> None:
        """Manually reset circuit to CLOSED"""
        logger.info("circuit_reset", name=self.name)
        self._transition_to_closed()

    def get_state(self) -> CircuitState:
        """Get current state"""
        return self.metrics.state

    def is_open(self) -> bool:
        """Check if circuit is open"""
        return self.metrics.state == CircuitState.OPEN

    def get_metrics(self) -> CircuitMetrics:
        """Get circuit metrics"""
        return self.metrics
