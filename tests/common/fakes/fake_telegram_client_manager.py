"""FakeTelegramClientManager — фейковая фабрика клиентов для тестов."""
from __future__ import annotations

from tg_exporter.services.telegram import ITelegramClientManager
from tg_exporter.services.telegram import TelegramClientInterface
from .fake_telegram_client import FakeTelegramClient


class FakeTelegramClientManager(ITelegramClientManager):
    """Фейковый менеджер. Создаёт FakeTelegramClient."""

    def __init__(self, client: FakeTelegramClient | None = None):
        self._client = client or FakeTelegramClient()
        self._session_override: str | None = None
        self._use_session_calls: list[str | None] = []

    async def create_connected_client(self) -> TelegramClientInterface:
        await self._client.connect()
        return self._client

    async def save_session(self) -> None:
        pass

    async def destroy(self) -> None:
        await self._client.destroy()

    def use_session(self, session_string: str | None) -> None:
        self._session_override = session_string
        self._use_session_calls.append(session_string)
