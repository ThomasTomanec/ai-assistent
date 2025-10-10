"""Async utilities"""
import asyncio
from typing import Callable, Any


async def run_in_thread(func: Callable, *args, **kwargs) -> Any:
    """Run blocking function in thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
