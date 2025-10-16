# src/infrastructure/adapters/ai/functionality/race_executor.py

"""Race Executor - Run cloud and local in parallel, take fastest"""

import asyncio
import time
from typing import Tuple, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class RaceResult:
    """Result from race execution"""
    winner: str  # "cloud" or "local"
    response: str
    winner_latency_ms: float
    loser_latency_ms: Optional[float] = None
    loser_error: Optional[str] = None


class RaceExecutor:
    """
    Execute cloud and local handlers in parallel.
    Return result from fastest one.
    """

    def __init__(self, winner_margin: float = 0.5):
        """
        Args:
            winner_margin: Minimum time difference to declare winner (seconds)
        """
        self.winner_margin = winner_margin
        logger.debug("race_executor_initialized", winner_margin=winner_margin)

    async def race(
            self,
            cloud_handler,
            local_handler,
            query: str
    ) -> RaceResult:
        """
        Race cloud vs local handler.

        Args:
            cloud_handler: Cloud model handler
            local_handler: Local model handler
            query: User query

        Returns:
            RaceResult with winner and metrics
        """
        logger.info("race_started", query=query[:50])

        # Start both tasks
        cloud_task = asyncio.create_task(self._execute_with_timing(
            cloud_handler.process(query), "cloud"
        ))
        local_task = asyncio.create_task(self._execute_with_timing(
            local_handler.process(query), "local"
        ))

        # Wait for first to complete
        done, pending = await asyncio.wait(
            [cloud_task, local_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Get first result
        first_task = done.pop()
        first_result, first_latency = await first_task
        first_handler = "cloud" if first_task == cloud_task else "local"

        # Wait for second (with timeout)
        second_task = pending.pop()
        try:
            second_result, second_latency = await asyncio.wait_for(
                second_task, timeout=5.0
            )
            second_error = None
        except asyncio.TimeoutError:
            logger.warning("race_second_timeout", winner=first_handler)
            second_latency = None
            second_error = "timeout"
        except Exception as e:
            logger.warning("race_second_error", error=str(e))
            second_latency = None
            second_error = str(e)

        # Determine winner
        result = RaceResult(
            winner=first_handler,
            response=first_result,
            winner_latency_ms=first_latency,
            loser_latency_ms=second_latency,
            loser_error=second_error
        )

        logger.info(
            "race_completed",
            winner=result.winner,
            winner_latency_ms=round(result.winner_latency_ms, 2),
            loser_latency_ms=round(result.loser_latency_ms, 2) if result.loser_latency_ms else None
        )

        return result

    async def _execute_with_timing(
            self,
            coro,
            name: str
    ) -> Tuple[str, float]:
        """Execute coroutine and measure time"""
        start = time.time()
        try:
            result = await coro
            latency_ms = (time.time() - start) * 1000
            return result, latency_ms
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            logger.error(f"{name}_execution_error", error=str(e), latency_ms=latency_ms)
            raise
