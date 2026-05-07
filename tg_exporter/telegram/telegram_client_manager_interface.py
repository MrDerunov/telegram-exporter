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
    def create_client(self) -> TelegramClientInterface:
        """Создать или вернуть готовый клиент."""
        ...

    @abstractmethod
    def save_session(self) -> None:
        """Сохранить текущую сессию."""
        ...

    @abstractmethod
    def destroy(self) -> None:
        """Уничтожить клиент."""
        ...
