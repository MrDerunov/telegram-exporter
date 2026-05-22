"""FakeTelegramServer — фейковый сервер Telegram для тестов.

Владеет всеми данными (пользователи, диалоги, сообщения, авторизация).
FakeTelegramClient делегирует все запросы этому серверу.

Использование в тестах:
    server = FakeTelegramServer()
    server.users.add_user(user)
    server.dialogs.add_dialog(dialog)
    server.messages.add_messages(peer_id, messages)
    server.auth.set_authorized(True)

    client = FakeTelegramClient(server)
"""

from __future__ import annotations

from datetime import datetime

from .fake_data_objects import FakeUser, FakeDialog, FakeMessage


class UserStore:
    """Хранилище фейковых пользователей."""

    def __init__(self) -> None:
        self._users: dict[int, FakeUser] = {}

    def add_user(self, user: FakeUser) -> None:
        self._users[user.id] = user

    def get_user(self, user_id: int) -> FakeUser | None:
        return self._users.get(user_id)

    def all_users(self) -> list[FakeUser]:
        return list(self._users.values())

    def clear(self) -> None:
        self._users.clear()


class DialogStore:
    """Хранилище фейковых диалогов."""

    def __init__(self) -> None:
        self._dialogs: dict[int, FakeDialog] = {}

    def add_dialog(self, dialog: FakeDialog) -> None:
        self._dialogs[dialog.id] = dialog

    def get_dialog(self, peer_id: int) -> FakeDialog | None:
        return self._dialogs.get(peer_id)

    def all_dialogs(self) -> list[FakeDialog]:
        return list(self._dialogs.values())

    def clear(self) -> None:
        self._dialogs.clear()


class MessageStore:
    """Хранилище фейковых сообщений.

    Сообщения индексируются по peer_id и сортируются по id.
    """

    def __init__(self) -> None:
        self._messages: dict[int, list[FakeMessage]] = {}

    def add_messages(self, peer_id: int, messages: list[FakeMessage]) -> None:
        existing = self._messages.setdefault(peer_id, [])
        existing.extend(messages)
        existing.sort(key=lambda m: m.id)

    def add_message(self, peer_id: int, message: FakeMessage) -> None:
        self.add_messages(peer_id, [message])

    def get_messages(self, peer_id: int) -> list[FakeMessage]:
        return list(self._messages.get(peer_id, []))

    def query(
        self,
        peer_id: int,
        min_id: int = 0,
        offset_date: datetime | None = None,
        limit: int | None = None,
        reply_to: int | None = None,
    ) -> list[FakeMessage]:
        """Выбрать сообщения с фильтрацией (как iter_messages)."""
        messages = self._messages.get(peer_id, [])
        filtered = [m for m in messages if m.id > min_id]
        if offset_date is not None:
            filtered = [
                m for m in filtered
                if m.date is not None and m.date > offset_date
            ]
        if limit is not None and limit > 0:
            filtered = filtered[:limit]
        return filtered

    def count(
        self,
        peer_id: int,
        min_id: int = 0,
        offset_date: datetime | None = None,
        reply_to: int | None = None,
    ) -> int:
        """Количество сообщений после фильтрации."""
        messages = self._messages.get(peer_id, [])
        filtered = [m for m in messages if m.id > min_id]
        if offset_date is not None:
            filtered = [
                m for m in filtered
                if m.date is not None and m.date > offset_date
            ]
        return len(filtered)

    def clear(self) -> None:
        self._messages.clear()


class AuthStore:
    """Хранилище состояния авторизации."""

    def __init__(self) -> None:
        self._authorized: bool = False
        self._code_requests: dict[str, str] = {}
        self._session_str: str = ""
        self._signed_in_user_id: int | None = None

    def set_authorized(self, authorized: bool) -> None:
        self._authorized = authorized

    def is_authorized(self) -> bool:
        return self._authorized

    def add_code_request(self, phone: str, code_hash: str) -> None:
        self._code_requests[phone] = code_hash

    def get_code_hash(self, phone: str) -> str | None:
        return self._code_requests.get(phone)

    def set_session(self, session_str: str) -> None:
        self._session_str = session_str

    def get_session(self) -> str:
        return self._session_str

    def set_user_id(self, user_id: int | None) -> None:
        self._signed_in_user_id = user_id

    def get_user_id(self) -> int | None:
        return self._signed_in_user_id

    def clear(self) -> None:
        self._authorized = False
        self._code_requests.clear()
        self._session_str = ""
        self._signed_in_user_id = None


class FakeTelegramServer:
    """Центральный компонент — владеет всеми хранилищами."""

    def __init__(self) -> None:
        self.users = UserStore()
        self.dialogs = DialogStore()
        self.messages = MessageStore()
        self.auth = AuthStore()

    def clear(self) -> None:
        """Полный сброс всех данных."""
        self.users.clear()
        self.dialogs.clear()
        self.messages.clear()
        self.auth.clear()
