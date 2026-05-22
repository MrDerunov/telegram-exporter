"""Компоненты фейкового сервера Telegram."""

from .fake_telegram_server import FakeTelegramServer
from .stores.user_store import UserStore
from .stores.dialog_store import DialogStore
from .stores.message_store import MessageStore
from .stores.auth_store import AuthStore

__all__ = [
    "FakeTelegramServer",
    "UserStore",
    "DialogStore",
    "MessageStore",
    "AuthStore",
]
