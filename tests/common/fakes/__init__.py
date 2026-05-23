"""Test doubles for tg-exporter."""
from .fake_telegram_client import FakeTelegramClient
from .fake_telegram_client_manager import FakeTelegramClientManager
from .fake_secret_store import FakeSecretStore
from .fake_settings_store import FakeSettingsStore
from .server import FakeTelegramServer
from .server.data_objects import (
    FakeUser,
    FakeChat,
    FakeFolder,
    FakeDialog,
    FakeMessage,
    FakeAction,
    FakeReplyTo,
    FakeFwdFrom,
    FakeReaction,
    FakeReactionResult,
    FakeReactions,
    FakePollAnswer,
    FakePoll,
    FakePollResultEntry,
    FakePollResults,
    FakePollMedia,
    FakeMessageEntityTextUrl,
    FakeMessageEntityUrl,
)

__all__ = [
    "FakeTelegramClient",
    "FakeTelegramClientManager",
    "FakeSecretStore",
    "FakeSettingsStore",
    "FakeTelegramServer",
    "FakeUser",
    "FakeChat",
    "FakeFolder",
    "FakeDialog",
    "FakeMessage",
    "FakeAction",
    "FakeReplyTo",
    "FakeFwdFrom",
    "FakeReaction",
    "FakeReactionResult",
    "FakeReactions",
    "FakePollAnswer",
    "FakePoll",
    "FakePollResultEntry",
    "FakePollResults",
    "FakePollMedia",
    "FakeMessageEntityTextUrl",
    "FakeMessageEntityUrl",
]
