"""Cancellation-aware serialization for thread-backed local storage."""

import asyncio
from collections.abc import Callable
from contextlib import suppress
from typing import ParamSpec, TypeVar

Parameters = ParamSpec("Parameters")
Result = TypeVar("Result")


async def run_sync(
    lock: asyncio.Lock,
    operation: Callable[Parameters, Result],
    *args: Parameters.args,
    **kwargs: Parameters.kwargs,
) -> Result:
    """Keep the lock until I/O completes, even when its caller is cancelled."""
    async with lock:
        worker = asyncio.create_task(asyncio.to_thread(operation, *args, **kwargs))
        try:
            return await asyncio.shield(worker)
        except asyncio.CancelledError:
            while not worker.done():
                with suppress(Exception, asyncio.CancelledError):
                    await asyncio.shield(worker)
            with suppress(Exception, asyncio.CancelledError):
                worker.result()
            raise
