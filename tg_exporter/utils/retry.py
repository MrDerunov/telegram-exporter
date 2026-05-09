"""Retry с экспоненциальной задержкой для сетевых операций."""
from __future__ import annotations

import asyncio
import random
from typing import Any, Callable, Coroutine, TypeVar

T = TypeVar("T")


async def retry_async(
    fn: Callable[..., Coroutine[Any, Any, T]],
    max_attempts: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    *args: Any,
    **kwargs: Any,
) -> T:
    """Выполняет async-функцию с экспоненциальным backoff.

    При неудаче повторяет до max_attempts раз с растущей задержкой.
    Задержка = min(base_delay * 2^(attempt-1) + jitter, max_delay).
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn(*args, **kwargs)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            last_exc = exc
            if attempt == max_attempts:
                break
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            jitter = random.uniform(0, delay * 0.1)
            await asyncio.sleep(delay + jitter)
    raise last_exc  # type: ignore[misc]
