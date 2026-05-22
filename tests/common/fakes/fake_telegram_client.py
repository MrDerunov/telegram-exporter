"""FakeTelegramClient — реализация TelegramClientInterface для тестов.

Делегирует все запросы FakeTelegramServer. Не хранит данные сам.
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Any
from collections.abc import AsyncIterator

from tg_exporter.services.telegram import TelegramClientInterface


class FakeTelegramClient(TelegramClientInterface):
    """Фейковый клиент, делегирующий все запросы FakeTelegramServer.

    Использование:
        server = FakeTelegramServer()
        server.auth.set_authorized(True)
        server.dialogs.add_dialog(dialog)
        server.messages.add_messages(peer_id, messages)

        client = FakeTelegramClient(server)
    """

    def __init__(self, server: Any = None):
        from .server.fake_telegram_server import FakeTelegramServer
        self._server: FakeTelegramServer = server or FakeTelegramServer()
        self._connected = False
        self.call_log: list[str] = []

    @property
    def server(self):
        """Доступ к серверу для настройки данных из тестов."""
        return self._server

    # ---- TelegramClientInterface ----

    async def connect(self) -> None:
        self.call_log.append("connect")
        self._connected = True

    async def disconnect(self) -> None:
        self.call_log.append("disconnect")
        self._connected = False

    async def is_authorized(self) -> bool:
        self.call_log.append("is_authorized")
        return self._server.auth.is_authorized()

    async def send_code_request(self, phone: str) -> Any:
        self.call_log.append(f"send_code_request({phone})")
        code_hash = f"hash_{phone}"
        self._server.auth.add_code_request(phone, code_hash)
        return type("SentCode", (), {"phone_code_hash": code_hash})()

    async def sign_in(self, phone: str, code: str) -> Any:
        self.call_log.append(f"sign_in({phone}, {code})")
        if code:
            self._server.auth.set_authorized(True)
            self._server.auth.set_user_id(12345)
        return type("User", (), {"id": 12345, "username": "test_user"})()

    async def sign_in_password(self, password: str) -> Any:
        self.call_log.append(f"sign_in_password({password})")
        if password:
            self._server.auth.set_authorized(True)
            self._server.auth.set_user_id(12345)
        return type("User", (), {"id": 12345, "username": "test_user"})()

    async def get_dialogs(self, limit: int | None = None) -> list[Any]:
        self.call_log.append(f"get_dialogs(limit={limit})")
        dialogs = self._server.dialogs.all_dialogs()
        if limit is not None:
            dialogs = dialogs[:limit]
        return dialogs

    async def iter_messages(
        self,
        peer_id: int,
        min_id: int = 0,
        offset_date: datetime | None = None,
        limit: int | None = None,
        reply_to: int | None = None,
    ) -> AsyncIterator[Any]:
        self.call_log.append(
            f"iter_messages(peer={peer_id}, min_id={min_id}, limit={limit})"
        )
        messages = self._server.messages.query(
            peer_id=peer_id,
            min_id=min_id,
            offset_date=offset_date,
            limit=limit,
            reply_to=reply_to,
        )
        for msg in messages:
            yield msg

    async def download_media(self, message: Any, path: Path) -> Path | None:
        self.call_log.append(f"download_media({getattr(message, 'id', '?')}, {path})")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return path

    async def destroy(self) -> None:
        self._connected = False

    async def log_out(self) -> None:
        self.call_log.append("log_out")
        self._server.auth.set_authorized(False)
        self._server.auth.set_user_id(None)

    async def count_messages(
        self,
        peer_id: int,
        min_id: int = 0,
        offset_date: datetime | None = None,
        reply_to: int | None = None,
    ) -> int | None:
        self.call_log.append(f"count_messages(peer={peer_id})")
        return self._server.messages.count(
            peer_id=peer_id,
            min_id=min_id,
            offset_date=offset_date,
            reply_to=reply_to,
        )
