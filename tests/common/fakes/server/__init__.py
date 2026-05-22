"""Компоненты фейкового сервера Telegram."""

from .fake_telegram_server import FakeTelegramServer
from common.fakes.server.stores.user_store import UserStore
from common.fakes.server.stores.dialog_store import DialogStore
from common.fakes.server.stores.message_store import MessageStore
from common.fakes.server.stores.auth_store import AuthStore

__all__ = [
    "FakeTelegramServer",
    "UserStore",
    "DialogStore",
    "MessageStore",
    "AuthStore",
]
