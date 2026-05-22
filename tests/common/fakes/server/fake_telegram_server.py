"""FakeTelegramServer — фейковый сервер Telegram для тестов.

Владеет всеми данными (пользователи, диалоги, сообщения, авторизация).
FakeTelegramClient делегирует все запросы этому серверу.
"""

from __future__ import annotations

from common.fakes.server.stores.user_store import UserStore
from common.fakes.server.stores.dialog_store import DialogStore
from common.fakes.server.stores.message_store import MessageStore
from common.fakes.server.stores.auth_store import AuthStore


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
