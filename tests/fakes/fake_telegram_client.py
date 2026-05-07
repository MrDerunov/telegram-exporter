"""FakeTelegramClient — реализация TelegramClientInterface для тестов.
Позволяет предзагружать диалоги и сообщения, симулировать авторизацию.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Any, AsyncIterator, Optional

from tg_exporter.core.client_interface import TelegramClientInterface


class FakeTelegramClient(TelegramClientInterface):
    """Фейковый клиент для unit-тестов.
    
    Позволяет:
    - Предзагружать диалоги и сообщения
    - Симулировать авторизацию/неавторизацию
    - Проверять что методы были вызваны с правильными параметрами
    - Тестировать экспорт на разных объёмах данных без реального API
    """

    def __init__(self):
        self._dialogs: list[Any] = []
        self._messages: dict[int, list[Any]] = {}  # peer_id → messages
        self._authorized = False
        self._session_str: str = ""
        self._connected = False
        # Для тестов: отслеживание вызовов
        self.call_log: list[str] = []

    # ---- Предзагрузка данных ----

    def add_dialog(self, dialog: Any) -> None:
        """Добавить диалог в список."""
        self._dialogs.append(dialog)

    def add_messages(self, peer_id: int, messages: list[Any]) -> None:
        """Добавить сообщения для чата."""
        self._messages[peer_id] = messages

    def set_authorized(self, authorized: bool) -> None:
        """Установить статус авторизации."""
        self._authorized = authorized

    def set_session(self, session_str: str) -> None:
        """Установить session string."""
        self._session_str = session_str

    # ---- Реализация интерфейса ----

    async def connect(self) -> None:
        self.call_log.append("connect")
        self._connected = True

    async def disconnect(self) -> None:
        self.call_log.append("disconnect")
        self._connected = False

    async def is_authorized(self) -> bool:
        self.call_log.append("is_authorized")
        return self._authorized

    async def send_code_request(self, phone: str) -> Any:
        self.call_log.append(f"send_code_request({phone})")
        return type("SentCode", (), {"phone_code_hash": "fake_hash"})()

    async def sign_in(self, phone: str, code: str) -> Any:
        self.call_log.append(f"sign_in({phone}, {code})")
        self._authorized = True
        return type("User", (), {"id": 12345, "username": "test_user"})()

    async def sign_in_password(self, password: str) -> Any:
        self.call_log.append(f"sign_in_password({password})")
        self._authorized = True
        return type("User", (), {"id": 12345, "username": "test_user"})()

    async def get_dialogs(self, limit: int | None = None) -> list[Any]:
        self.call_log.append(f"get_dialogs(limit={limit})")
        dialogs = self._dialogs
        if limit is not None:
            dialogs = dialogs[:limit]
        return dialogs

    async def iter_messages(
        self, peer_id: int, min_id: int = 0,
        offset_date: datetime | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[Any]:
        self.call_log.append(f"iter_messages(peer={peer_id}, min_id={min_id}, limit={limit})")
        messages = self._messages.get(peer_id, [])
        # Фильтр по min_id
        filtered = [m for m in messages if getattr(m, 'id', 0) > min_id]
        # Фильтр по offset_date
        if offset_date is not None:
            filtered = [m for m in filtered if getattr(m, 'date', datetime.min) >= offset_date]
        # Лимит
        if limit is not None:
            filtered = filtered[:limit]
        for msg in filtered:
            yield msg

    async def download_media(self, message: Any, path: Path) -> Path | None:
        self.call_log.append(f"download_media({getattr(message, 'id', '?')}, {path})")
        # Создаём пустой файл как заглушку
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return path

    def save_session(self) -> str:
        self.call_log.append("save_session")
        return self._session_str

    def load_session(self, session_str: str) -> None:
        self.call_log.append(f"load_session(...)")
        self._session_str = session_str
