"""Fake-объекты, имитирующие Telethon-типы для тестов."""

from .fake_user import FakeUser
from .fake_chat import FakeChat
from .fake_folder import FakeFolder
from .fake_dialog import FakeDialog
from .fake_message import FakeMessage
from .fake_action import FakeAction
from .fake_reply_to import FakeReplyTo
from .fake_fwd_from import FakeFwdFrom
from .fake_reactions import FakeReaction, FakeReactionResult, FakeReactions
from .fake_poll import FakePollAnswer, FakePoll, FakePollResultEntry, FakePollResults, FakePollMedia
from .fake_message_entities import FakeMessageEntityTextUrl, FakeMessageEntityUrl

__all__ = [
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
