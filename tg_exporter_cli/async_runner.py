"""AsyncRunner — запуск async-кода из синхронных Click-команд."""
import asyncio
from typing import Coroutine, Any


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """Запустить корутину в новом event loop."""
    return asyncio.run(coro)
