"""FakeTelegramClientManager — фейковая фабрика клиентов для тестов."""
from __future__ import annotations

from tg_exporter.telegram.telegram_client_manager_interface import ITelegramClientManager
from tg_exporter.telegram.telegram_client_interface import TelegramClientInterface
from .fake_telegram_client import FakeTelegramClient


class FakeTelegramClientManager(ITelegramClientManager):
    """Фейковый менеджер. Создаёт FakeTelegramClient."""

    def __init__(self, client: FakeTelegramClient | None = None):
        self._client = client or FakeTelegramClient()

    def create_client(self) -> TelegramClientInterface:
        return self._client

    async def save_session(self) -> None:
        pass

    async def destroy(self) -> None:
        await self._client.destroy()
