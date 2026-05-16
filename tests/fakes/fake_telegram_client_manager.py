"""FakeTelegramClientManager — фейковая фабрика клиентов для тестов."""
from __future__ import annotations

from tg_exporter.services.telegram import ITelegramClientManager
from tg_exporter.services.telegram import TelegramClientInterface
from .fake_telegram_client import FakeTelegramClient


class FakeTelegramClientManager(ITelegramClientManager):
    """Фейковый менеджер. Создаёт FakeTelegramClient."""

    def __init__(self, client: FakeTelegramClient | None = None):
        self._client = client or FakeTelegramClient()

    async def create_connected_client(self) -> TelegramClientInterface:
        await self._client.connect()
        return self._client

    async def save_session(self) -> None:
        pass

    async def destroy(self) -> None:
        await self._client.destroy()
