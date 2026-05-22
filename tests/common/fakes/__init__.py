"""Test doubles for tg-exporter."""
from .fake_telegram_client import FakeTelegramClient
from .fake_telegram_client_manager import FakeTelegramClientManager
from .server import FakeTelegramServer
from common.fakes.server.data_objects import (
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
