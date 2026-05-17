"""TelethonClientAdapter — реализация TelegramClientInterface через telethon."""
from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any, Optional
from collections.abc import AsyncIterator
from datetime import datetime

from telethon import TelegramClient
from telethon.sessions import StringSession

from .telegram_client_interface import TelegramClientInterface


class TelethonClientAdapter(TelegramClientInterface):
    """Реализует интерфейс напрямую через telethon.TelegramClient."""

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_str: str = "",
    ) -> None:
        self._api_id = api_id
        self._api_hash = api_hash
        self._session_str = session_str
        self._client: TelegramClient | None = None
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    # ---- Event loop ----

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        """Гарантирует наличие event loop в текущем потоке."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("closed")
            return loop
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            return loop

    def _build_client(self) -> TelegramClient:
        """Создаёт telethon-клиент."""
        session = StringSession(self._session_str) if self._session_str else StringSession()
        return TelegramClient(session, self._api_id, self._api_hash)

    # ---- TelegramClientInterface ----

    async def connect(self) -> None:
        self._ensure_loop()
        with self._lock:
            if self._client is None:
                self._client = self._build_client()
        if not self._client.is_connected():
            await self._client.connect()

    async def disconnect(self) -> None:
        with self._lock:
            if self._client is not None:
                try:
                    await self._client.disconnect()
                except Exception:
                    pass

    async def is_authorized(self) -> bool:
        if self._client is None:
            return False
        return await self._client.is_user_authorized()

    async def send_code_request(self, phone: str) -> Any:
        if self._client is None:
            await self.connect()
        return await self._client.send_code_request(phone)

    async def sign_in(self, phone: str, code: str) -> Any:
        return await self._client.sign_in(phone=phone, code=code)

    async def sign_in_password(self, password: str) -> Any:
        return await self._client.sign_in(password=password)

    async def get_dialogs(self, limit: int | None = None) -> list[Any]:
        if self._client is None:
            await self.connect()
        return await self._client.get_dialogs(limit=limit)

    async def iter_messages(
        self, peer_id: int, min_id: int = 0,
        offset_date: datetime | None = None,
        limit: int | None = None,
        reply_to: int | None = None,
    ) -> AsyncIterator[Any]:
        if self._client is None:
            await self.connect()
        async for msg in self._client.iter_messages(
            peer_id, min_id=min_id, offset_date=offset_date, limit=limit,
            reverse=True, reply_to=reply_to,
        ):
            yield msg

    async def download_media(self, message: Any, path: Path) -> Path | None:
        if self._client is None:
            await self.connect()
        result = await self._client.download_media(message, str(path))
        return Path(result) if result else None

    async def save_session(self) -> str:
        """Сохраняет и возвращает текущую сессию."""
        with self._lock:
            if self._client is None:
                return ""
            try:
                return self._client.session.save() or ""
            except Exception:
                return ""

    def load_session(self, session_str: str) -> None:
        """Загружает сессию. Требует пересоздания клиента."""
        with self._lock:
            self._session_str = session_str
            if self._client is not None:
                try:
                    self._client.disconnect()
                except Exception:
                    pass
            self._client = None

    async def destroy(self) -> None:
        """Уничтожает клиент (для logout)."""
        with self._lock:
            if self._client is not None:
                try:
                    await self._client.disconnect()
                except Exception:
                    pass
                self._client = None

    async def log_out(self) -> None:
        """Выход из аккаунта на сервере Telegram."""
        if self._client is not None:
            await self._client.log_out()

    async def count_messages(
        self,
        peer_id: int,
        min_id: int = 0,
        offset_date: datetime | None = None,
        reply_to: int | None = None,
    ) -> int | None:
        if self._client is None:
            await self.connect()
        kwargs: dict = {"limit": 0}
        if min_id:
            kwargs["min_id"] = min_id
        if offset_date:
            kwargs["offset_date"] = offset_date
        if reply_to is not None:
            kwargs["reply_to"] = reply_to
        try:
            messages = await self._client.get_messages(peer_id, **kwargs)
            return messages.total
        except Exception:
            return None
