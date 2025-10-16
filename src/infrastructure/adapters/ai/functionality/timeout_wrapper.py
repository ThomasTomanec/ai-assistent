# src/infrastructure/adapters/ai/functionality/timeout_wrapper.py

"""Async Timeout Wrapper"""

import asyncio
from typing import Callable, TypeVar, Any
import structlog

logger = structlog.get_logger()

T = TypeVar('T')


class TimeoutError(Exception):
    """Timeout exception"""
    pass


async def with_timeout(
        coro: Callable,
        timeout: float,
        name: str = "operation"
) -> Any:
    """
    Execute coroutine with timeout.

    Args:
        coro: Coroutine to execute
        timeout: Timeout in seconds
        name: Operation name for logging

    Returns:
        Result from coroutine

    Raises:
        TimeoutError: If timeout exceeded
    """
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
        return result
    except asyncio.TimeoutError:
        logger.warning("operation_timeout", name=name, timeout=timeout)
        raise TimeoutError(f"{name} timed out after {timeout}s")
