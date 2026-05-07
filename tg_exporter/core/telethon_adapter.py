"""
TelethonClientAdapter — обёртка над TelegramClientManager,
реализующая контракт TelegramClientInterface.

Делегирует все вызовы в TelegramClientManager / Telethon-клиент.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, AsyncIterator, Optional
from datetime import datetime

from .client_interface import TelegramClientInterface
from .client import TelegramClientManager


class TelethonClientAdapter(TelegramClientInterface):
    """
    Адаптер, оборачивающий TelegramClientManager в интерфейс TelegramClientInterface.

    Предоставляет метод get_client() для обратной совместимости —
    возвращает «сырой» Telethon-клиент (результат ensure_connected).
    """

    def __init__(self, manager: TelegramClientManager) -> None:
        self._manager = manager

    # ---- Compatibility bridge (не часть интерфейса) ----

    def get_client(self):
        """
        Возвращает готовый подключённый Telethon-клиент.
        Используется кодом, который ещё не переведён на интерфейс.
        """
        return self._manager.ensure_connected()

    # ---- TelegramClientInterface implementation ----

    async def connect(self) -> None:
        self._manager.ensure_connected()

    async def disconnect(self) -> None:
        self._manager.disconnect()

    async def is_authorized(self) -> bool:
        c = self._manager.ensure_connected()
        return c.is_user_authorized()

    async def send_code_request(self, phone: str) -> Any:
        c = self._manager.ensure_connected()
        return c.send_code_request(phone)

    async def sign_in(self, phone: str, code: str) -> Any:
        c = self._manager.ensure_connected()
        return c.sign_in(phone=phone, code=code)

    async def sign_in_password(self, password: str) -> Any:
        c = self._manager.ensure_connected()
        return c.sign_in(password=password)

    async def get_dialogs(
        self, limit: int | None = None
    ) -> list[Any]:
        c = self._manager.ensure_connected()
        return c.get_dialogs(limit=limit)

    async def iter_messages(
        self,
        peer_id: int,
        min_id: int = 0,
        offset_date: datetime | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[Any]:
        c = self._manager.ensure_connected()
        entity = c.get_input_entity(peer_id)
        for msg in c.iter_messages(
            entity,
            min_id=min_id,
            offset_date=offset_date,
            limit=limit,
        ):
            yield msg

    async def download_media(
        self, message: Any, path: Path
    ) -> Path | None:
        c = self._manager.ensure_connected()
        result = c.download_media(message, str(path))
        return Path(result) if result else None

    def save_session(self) -> str:
        self._manager.save_session()
        if self._manager._client is not None:
            return self._manager._client.session.save()
        return ""

    def load_session(self, session_str: str) -> None:
        self._manager.use_session(session_str)
