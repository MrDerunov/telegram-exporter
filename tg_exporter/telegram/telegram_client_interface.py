"""
TelegramClientInterface — абстрактный контракт для взаимодействия с Telegram API.

Позволяет подменять реализацию клиента (Telethon, Pyrogram, etc.)
без изменения бизнес-логики.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional
from collections.abc import AsyncIterator
from datetime import datetime


class TelegramClientInterface(ABC):
    """Контракт для взаимодействия с Telegram API."""

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def is_authorized(self) -> bool: ...

    @abstractmethod
    async def send_code_request(self, phone: str) -> Any: ...

    @abstractmethod
    async def sign_in(self, phone: str, code: str) -> Any: ...

    @abstractmethod
    async def sign_in_password(self, password: str) -> Any: ...

    @abstractmethod
    async def get_dialogs(
        self, limit: int | None = None
    ) -> list[Any]: ...

    @abstractmethod
    async def iter_messages(
        self,
        peer_id: int,
        min_id: int = 0,
        offset_date: datetime | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[Any]: ...

    @abstractmethod
    async def download_media(
        self, message: Any, path: Path
    ) -> Path | None: ...

    @abstractmethod
    async def destroy(self) -> None:
        """Уничтожить клиент (для logout)."""
        ...

    @abstractmethod
    async def log_out(self) -> None:
        """Выход из аккаунта на сервере Telegram."""
        ...

    @abstractmethod
    async def count_messages(
        self,
        peer_id: int,
        min_id: int = 0,
        offset_date: datetime | None = None,
        reply_to: int | None = None,
    ) -> int | None:
        """Вернуть количество сообщений в чате (или None если не удалось)."""
        ...
