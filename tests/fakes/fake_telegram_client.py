"""FakeTelegramClient — реализация TelegramClientInterface для тестов.
Позволяет предзагружать диалоги и сообщения, симулировать авторизацию.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

from tg_exporter.telegram.telegram_client_interface import TelegramClientInterface


class _FakeMessageIter:
    """Sync-iterable wrapper для списка сообщений (эмулирует Telethon _MessagesIter)."""

    def __init__(self, messages: list[Any]) -> None:
        self._messages = messages
        self.total = len(messages)

    def __iter__(self):
        return iter(self._messages)

    def __len__(self) -> int:
        return len(self._messages)


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

    def iter_messages(
        self, entity, min_id: int = 0,
        offset_date: datetime | None = None,
        limit: int | None = None,
        reverse: bool = False,
        reply_to: int | None = None,
    ):
        """Синхронный итератор (как в Telethon). Эмулирует telethon.client.messages.MessageMethods.iter_messages."""
        # Поддержка как int peer_id, так и entity с .id
        peer_id = entity if isinstance(entity, int) else getattr(entity, 'id', 0)
        self.call_log.append(f"iter_messages(peer={peer_id}, min_id={min_id}, limit={limit})")
        messages = self._messages.get(peer_id, [])
        # Фильтр по min_id
        filtered = [m for m in messages if getattr(m, 'id', 0) > min_id]
        # Фильтр по offset_date
        if offset_date is not None:
            filtered = [m for m in filtered if getattr(m, 'date', datetime.min) >= offset_date]
        # reverse
        if reverse:
            filtered = list(reversed(filtered))
        # Лимит
        if limit is not None and limit > 0:
            filtered = filtered[:limit]
        # Возвращаем sync-iterable (как Telethon)
        return _FakeMessageIter(filtered)

    async def download_media(self, message: Any, path: Path) -> Path | None:
        self.call_log.append(f"download_media({getattr(message, 'id', '?')}, {path})")
        # Создаём пустой файл как заглушку
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return path

    async def save_session(self) -> str:
        self.call_log.append("save_session")
        return self._session_str

    def load_session(self, session_str: str) -> None:
        self.call_log.append(f"load_session(...)")
        self._session_str = session_str

    def get_messages(self, entity, **kwargs) -> Any:
        """Эмуляция telethon.client.messages.MessageMethods.get_messages."""
        peer_id = entity if isinstance(entity, int) else getattr(entity, 'id', 0)
        messages = self._messages.get(peer_id, [])
        total = len(messages)
        return type("TotalList", (), {"total": total, "__len__": lambda s: total})()

    async def destroy(self) -> None:
        self._connected = False

    async def log_out(self) -> None:
        self.call_log.append("log_out")
        self._authorized = False

    async def count_messages(
        self,
        peer_id: int,
        min_id: int = 0,
        offset_date: datetime | None = None,
        reply_to: int | None = None,
    ) -> int | None:
        self.call_log.append(f"count_messages(peer={peer_id})")
        return len(self._messages.get(peer_id, []))
