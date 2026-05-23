"""
ITelegramClientManager — интерфейс фабрики Telegram-клиентов.

Позволяет подменять реализацию (реальный Telethon / фейковый для тестов).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .telegram_client_interface import TelegramClientInterface


class ITelegramClientManager(ABC):
    """Контракт для фабрики клиентов Telegram."""

    @abstractmethod
    async def create_connected_client(self) -> TelegramClientInterface:
        """Создать и подключить клиент."""
        ...

    @abstractmethod
    async def save_session(self) -> None:
        """Сохранить текущую сессию."""
        ...

    @abstractmethod
    async def destroy(self) -> None:
        """Уничтожить клиент."""
        ...

    @abstractmethod
    def use_session(self, session_string: str | None) -> None:
        """Указать конкретную сессию (для переключения профилей).
        После вызова следующий create_connected_client() использует эту сессию."""
        ...
