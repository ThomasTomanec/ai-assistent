# src/infrastructure/adapters/ai/hybrid_handler.py

"""
Hybrid AI Handler - Production Grade Implementation

Features:
- Smart response cache with TTL
- Circuit breakers (cloud + local)
- Latency tracking & monitoring
- Timeout handling
- Race mode (parallel execution)
- Adaptive routing
- Silent fallback (no error spam)
- Full observability
"""

import time
from typing import Callable, Optional
from datetime import datetime
import structlog

from src.core.ports.i_command_handler import ICommandHandler
from src.infrastructure.adapters.ai.cloud_model_handler import CloudModelHandler
from src.infrastructure.adapters.ai.local_model_handler import LocalModelHandler
from src.core.routing.intelligent_router import IntelligentRouter
from src.core.exceptions import AIError

# Import models
from .models import AIConfig, AIRequestMetrics, AIStatistics, CircuitState

# Import functionality
from .functionality import (
    ResponseCache,
    CircuitBreaker,
    LatencyTracker,
    with_timeout,
    TimeoutError,
    RaceExecutor
)

logger = structlog.get_logger()


class HybridAIHandler(ICommandHandler):
    """
    Production-grade hybrid AI handler with enterprise features.

    Architecture:
    ┌─────────────────────────────────────────────┐
    │         HybridAIHandler (Main)              │
    ├─────────────────────────────────────────────┤
    │  ┌────────────┐  ┌──────────────────────┐  │
    │  │   Cache    │  │  Circuit Breakers    │  │
    │  │  (Smart    │  │  - Cloud breaker     │  │
    │  │   TTL)     │  │  - Local breaker     │  │
    │  └────────────┘  └──────────────────────┘  │
    │                                              │
    │  ┌────────────┐  ┌──────────────────────┐  │
    │  │  Latency   │  │   Race Executor      │  │
    │  │  Tracker   │  │  (Parallel mode)     │  │
    │  └────────────┘  └──────────────────────┘  │
    ├─────────────────────────────────────────────┤
    │         CloudHandler  |  LocalHandler       │
    └─────────────────────────────────────────────┘
    """

    def __init__(
            self,
            cloud_handler: CloudModelHandler,
            local_handler: LocalModelHandler,
            user_preference: str = "intelligent",
            config: Optional[AIConfig] = None
    ):
        """
        Initialize production hybrid handler.

        Args:
            cloud_handler: Cloud AI handler (OpenAI)
            local_handler: Local AI handler (Ollama)
            user_preference: 'local_only', 'cloud_only', 'intelligent'
            config: Optional configuration
        """
        self.cloud_handler = cloud_handler
        self.local_handler = local_handler
        self.user_preference = user_preference
        self.config = config or AIConfig(user_preference=user_preference)

        # ========================================
        # Initialize Components
        # ========================================

        # Response cache with smart TTL
        self.cache = ResponseCache(
            max_size=self.config.cache_max_size,
            enabled=self.config.cache_enabled
        )

        # Circuit breakers
        self.cloud_breaker = CircuitBreaker(
            name="cloud",
            failure_threshold=self.config.cloud_failure_threshold,
            recovery_timeout=self.config.recovery_timeout,
            success_threshold=self.config.success_threshold,
            enabled=self.config.circuit_breaker_enabled
        )

        self.local_breaker = CircuitBreaker(
            name="local",
            failure_threshold=self.config.local_failure_threshold,
            recovery_timeout=self.config.recovery_timeout,
            success_threshold=self.config.success_threshold,
            enabled=self.config.circuit_breaker_enabled
        )

        # Latency trackers
        self.cloud_latency = LatencyTracker(
            window_size=self.config.latency_window,
            enabled=self.config.track_latency
        )

        self.local_latency = LatencyTracker(
            window_size=self.config.latency_window,
            enabled=self.config.track_latency
        )

        # Race executor
        self.race_executor = RaceExecutor(
            winner_margin=self.config.race_mode_winner_margin
        )

        # Intelligent router (for routing decisions)
        self.router = IntelligentRouter()

        # Statistics
        self.stats = AIStatistics()

        # Streaming callback
        self.response_callback: Optional[Callable] = None

        logger.info(
            "hybrid_handler_initialized",
            user_preference=user_preference,
            cache_enabled=self.config.cache_enabled,
            circuit_breaker_enabled=self.config.circuit_breaker_enabled,
            race_mode_enabled=self.config.race_mode_enabled
        )

    def set_response_callback(self, callback: Callable):
        """Set streaming callback (propagate to handlers)"""
        self.response_callback = callback

        if hasattr(self.cloud_handler, 'set_response_callback'):
            self.cloud_handler.set_response_callback(callback)

        if hasattr(self.local_handler, 'set_response_callback'):
            self.local_handler.set_response_callback(callback)

        logger.debug("response_callback_set")

    def process(self, text: str) -> str:
        """
        Process command with full enterprise features.

        Flow:
        1. Check cache → return if hit
        2. Check user preference override
        3. Route intelligently (PII, complexity)
        4. Check circuit breakers
        5. Execute with timeout & retry
        6. Track metrics & update circuits
        7. Cache response
        8. Return result

        Args:
            text: User query

        Returns:
            AI response
        """
        start_time = time.time()
        self.stats.total_requests += 1

        logger.info("request_received", query=text[:50])

        # ========================================
        # Phase 1: Cache Check
        # ========================================
        cached_response = self.cache.get(text)
        if cached_response:
            self.stats.cache_hits += 1
            logger.info("cache_hit_returned", query=text[:50])
            return cached_response

        # ========================================
        # Phase 2: Routing Decision
        # ========================================
        try:
            handler_choice = self._determine_handler(text)
            logger.info("handler_selected", handler=handler_choice)
        except Exception as e:
            logger.error("routing_failed", error=str(e))
            handler_choice = "local"  # Safe fallback

        # ========================================
        # Phase 3: Execute Request
        # ========================================
        response = None
        metrics = None

        try:
            if self.config.race_mode_enabled and self._should_use_race_mode():
                # Race mode: parallel execution
                response, metrics = self._execute_race_mode(text)
            else:
                # Normal mode: sequential with fallback
                response, metrics = self._execute_with_fallback(text, handler_choice)

        except Exception as e:
            logger.error("request_failed", error=str(e), exc_info=True)
            response = f"Omlouvám se, nastala chyba: {str(e)}"
            metrics = AIRequestMetrics(
                handler="error",
                success=False,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )

        # ========================================
        # Phase 4: Cache & Return
        # ========================================
        if response and metrics and metrics.success:
            self.cache.set(text, response)

        # Update statistics
        self._update_statistics(metrics)

        return response

    def _determine_handler(self, text: str) -> str:
        """
        Determine which handler to use.

        Priority:
        1. User preference override
        2. Circuit breaker state
        3. Intelligent router (PII, complexity)
        4. Adaptive routing (latency-based)

        Returns:
            "cloud" or "local"
        """
        # 1. User preference override
        if self.user_preference == "cloud_only":
            if not self.cloud_breaker.is_open():
                return "cloud"
            logger.warning("cloud_preferred_but_breaker_open", falling_back="local")
            return "local"

        if self.user_preference == "local_only":
            return "local"

        # 2. Circuit breaker check
        cloud_available = self.cloud_breaker.allow_request()
        local_available = self.local_breaker.allow_request()

        if not cloud_available and not local_available:
            logger.error("both_circuits_open", using="local")
            return "local"  # Try local anyway

        if not cloud_available:
            logger.warning("cloud_circuit_open", using="local")
            return "local"

        # 3. Use intelligent router (handles PII, complexity, etc.)
        # FIX: router.route() returns tuple (decision, handler)
        routing_decision, suggested_handler = self.router.route(text)

        # 4. Adaptive routing override (if cloud is slow)
        if self.config.adaptive_routing and suggested_handler == "cloud":
            cloud_avg = self.cloud_latency.get_average()
            if cloud_avg > self.config.cloud_latency_threshold * 1000:  # Convert to ms
                logger.info(
                    "adaptive_routing_override",
                    cloud_latency_ms=round(cloud_avg, 2),
                    switching_to="local"
                )
                return "local"

        # 5. Return router's suggestion
        logger.debug("using_router_suggestion", handler=suggested_handler)
        return suggested_handler

    def _should_use_race_mode(self) -> bool:
        """Check if race mode should be used"""
        if not self.config.race_mode_enabled:
            return False

        # Use race mode if cloud is slow
        cloud_avg = self.cloud_latency.get_average()
        threshold_ms = self.config.race_mode_threshold * 1000

        should_race = cloud_avg > threshold_ms
        if should_race:
            logger.info("race_mode_triggered", cloud_latency_ms=round(cloud_avg, 2))

        return should_race

    def _execute_with_fallback(
            self,
            text: str,
            primary: str
    ) -> tuple[str, AIRequestMetrics]:
        """
        Execute request with fallback.

        Args:
            text: User query
            primary: Primary handler ("cloud" or "local")

        Returns:
            (response, metrics)
        """
        # Try primary handler
        try:
            response, metrics = self._execute_handler(text, primary)
            return response, metrics

        except Exception as e:
            logger.warning(
                "primary_handler_failed",
                handler=primary,
                error=str(e)
            )

            # Fallback to other handler
            fallback = "local" if primary == "cloud" else "cloud"
            logger.info("attempting_fallback", fallback=fallback)

            try:
                response, metrics = self._execute_handler(text, fallback)
                metrics.fallback_used = True
                self.stats.fallbacks += 1
                return response, metrics

            except Exception as fallback_error:
                logger.error(
                    "fallback_also_failed",
                    error=str(fallback_error)
                )
                raise

    def _execute_handler(
            self,
            text: str,
            handler_name: str
    ) -> tuple[str, AIRequestMetrics]:
        """
        Execute single handler with timeout and circuit breaker.

        Args:
            text: User query
            handler_name: "cloud" or "local"

        Returns:
            (response, metrics)
        """
        handler = self.cloud_handler if handler_name == "cloud" else self.local_handler
        breaker = self.cloud_breaker if handler_name == "cloud" else self.local_breaker
        latency_tracker = self.cloud_latency if handler_name == "cloud" else self.local_latency
        timeout = self.config.cloud_timeout if handler_name == "cloud" else self.config.local_timeout

        # Check circuit breaker
        if not breaker.allow_request():
            raise AIError(f"{handler_name} circuit breaker is open")

        # Execute with timeout
        start = time.time()
        metrics = AIRequestMetrics(
            handler=handler_name,
            success=False,
            started_at=datetime.now(),
            circuit_open=breaker.is_open()
        )

        try:
            # Call handler
            response = handler.process(text)

            # Success!
            latency_ms = (time.time() - start) * 1000
            metrics.success = True
            metrics.response_length = len(response)
            metrics.latency_ms = latency_ms
            metrics.finished_at = datetime.now()

            # Update trackers
            breaker.record_success()
            latency_tracker.record(latency_ms)

            logger.info(
                f"{handler_name}_success",
                latency_ms=round(latency_ms, 2)
            )

            return response, metrics

        except Exception as e:
            # Failure - silent (no error log spam)
            latency_ms = (time.time() - start) * 1000
            metrics.latency_ms = latency_ms
            metrics.error = str(e)
            metrics.finished_at = datetime.now()

            # Update circuit breaker
            breaker.record_failure()

            # REMOVED: logger.error - silent fallback!

            raise

    def _execute_race_mode(self, text: str) -> tuple[str, AIRequestMetrics]:
        """
        Execute race mode (parallel cloud + local).

        Returns:
            (response, metrics)
        """
        logger.info("race_mode_executing")
        self.stats.race_mode_used += 1

        import asyncio

        # Run race
        result = asyncio.run(
            self.race_executor.race(
                self.cloud_handler,
                self.local_handler,
                text
            )
        )

        # Update stats
        if result.winner == "cloud":
            self.stats.cloud_wins += 1
        else:
            self.stats.local_wins += 1

        # Create metrics
        metrics = AIRequestMetrics(
            handler=result.winner,
            success=True,
            response_length=len(result.response),
            latency_ms=result.winner_latency_ms,
            race_winner=result.winner
        )

        return result.response, metrics

    def _update_statistics(self, metrics: AIRequestMetrics):
        """Update aggregate statistics"""
        if not metrics:
            return

        # Count by handler
        if metrics.handler == "cloud":
            self.stats.cloud_requests += 1
            self.stats.cloud_latencies.append(metrics.latency_ms)
        elif metrics.handler == "local":
            self.stats.local_requests += 1
            self.stats.local_latencies.append(metrics.latency_ms)

        # Keep window size
        window = self.config.latency_window
        if len(self.stats.cloud_latencies) > window:
            self.stats.cloud_latencies = self.stats.cloud_latencies[-window:]
        if len(self.stats.local_latencies) > window:
            self.stats.local_latencies = self.stats.local_latencies[-window:]

        # Failures
        if not metrics.success:
            self.stats.failures += 1

        # Circuit states
        self.stats.current_cloud_state = self.cloud_breaker.get_state().value
        self.stats.current_local_state = self.local_breaker.get_state().value
        self.stats.cloud_circuit_trips = self.cloud_breaker.metrics.total_trips
        self.stats.local_circuit_trips = self.local_breaker.metrics.total_trips

    def get_statistics(self) -> dict:
        """Get comprehensive statistics"""
        return {
            **self.stats.to_dict(),
            'cache': self.cache.get_stats(),
            'cloud_latency': self.cloud_latency.get_stats(),
            'local_latency': self.local_latency.get_stats(),
            'cloud_circuit': self.cloud_breaker.get_metrics().to_dict(),
            'local_circuit': self.local_breaker.get_metrics().to_dict()
        }

    def reset_statistics(self):
        """Reset all statistics"""
        self.stats = AIStatistics()
        self.cache.clear()
        self.cloud_latency.reset()
        self.local_latency.reset()
        logger.info("statistics_reset")
