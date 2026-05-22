"""Fake-объекты, имитирующие Telethon-типы для тестов.

Каждый класс содержит только те поля, которые читаются production-кодом
(converter.py, export_orchestrator.py, media_downloader.py, chats.py, export.py).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# User / Chat / Entity
# ---------------------------------------------------------------------------

class FakeUser:
    """Заглушка Telethon User (и совместимость с Chat/Channel).

    converter.py вызывает get_display_name(message.sender), который читает
    .first_name, .last_name (User) или .title (Chat/Channel).
    """

    def __init__(
        self,
        id: int = 0,
        first_name: str | None = None,
        last_name: str | None = None,
        username: str | None = None,
        title: str | None = None,
    ) -> None:
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.title = title


class FakeChat:
    """Заглушка для dialog.entity (Chat/Channel)."""

    def __init__(
        self,
        id: int = 0,
        title: str = "",
        username: str = "",
        broadcast: bool = False,
    ) -> None:
        self.id = id
        self.title = title
        self.username = username
        self.broadcast = broadcast


class FakeFolder:
    """Заглушка dialog.folder."""

    def __init__(self, id: int = 0, title: str | None = None) -> None:
        self.id = id
        self.title = title


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class FakeDialog:
    """Заглушка Telethon Dialog.

    Поля, читаемые кодом: .id, .name, .title, .entity (с .username, .broadcast),
    .is_user, .is_group, .is_channel, .message (.date), .folder (.title).
    """

    def __init__(
        self,
        id: int = 0,
        name: str = "",
        title: str = "",
        entity: FakeUser | FakeChat | None = None,
        is_user: bool = False,
        is_group: bool = False,
        is_channel: bool = False,
        message: FakeMessage | None = None,
        folder: FakeFolder | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.title = title
        self.entity = entity
        self.is_user = is_user
        self.is_group = is_group
        self.is_channel = is_channel
        self.message = message
        self.folder = folder


# ---------------------------------------------------------------------------
# Message sub-objects
# ---------------------------------------------------------------------------

class FakeAction:
    """Заглушка message.action (MessageActionTopicEdit и др.)."""

    def __init__(self, title: str | None = None) -> None:
        self.title = title


class FakeReplyTo:
    """Заглушка message.reply_to (MessageReplyHeader)."""

    def __init__(
        self,
        top_msg_id: int | None = None,
        reply_to_top_id: int | None = None,
        forum_topic: bool | None = None,
    ) -> None:
        self.top_msg_id = top_msg_id
        self.reply_to_top_id = reply_to_top_id
        self.forum_topic = forum_topic


class FakeFwdFrom:
    """Заглушка message.fwd_from (MessageFwdHeader)."""

    def __init__(
        self,
        from_name: str | None = None,
        from_id: int | None = None,
        channel_post: int | None = None,
    ) -> None:
        self.from_name = from_name
        self.from_id = from_id
        self.channel_post = channel_post


# ---------------------------------------------------------------------------
# Reactions
# ---------------------------------------------------------------------------

class FakeReaction:
    """Заглушка Reaction (эмодзи)."""

    def __init__(self, emoticon: str = "") -> None:
        self.emoticon = emoticon


class FakeReactionResult:
    """Заглушка ReactionResult (реакция + количество)."""

    def __init__(self, reaction: FakeReaction | None = None, count: int = 0) -> None:
        self.reaction = reaction or FakeReaction()
        self.count = count


class FakeReactions:
    """Заглушка message.reactions (MessageReactions)."""

    def __init__(self, results: list[FakeReactionResult] | None = None) -> None:
        self.results = results or []


# ---------------------------------------------------------------------------
# Poll
# ---------------------------------------------------------------------------

class FakePollAnswer:
    """Заглушка PollAnswer."""

    def __init__(self, option: bytes = b"", text: str = "") -> None:
        self.option = option
        self.text = text


class FakePoll:
    """Заглушка Poll (опрос)."""

    def __init__(
        self,
        id: int = 0,
        question: str = "",
        answers: list[FakePollAnswer] | None = None,
    ) -> None:
        self.id = id
        self.question = question
        self.answers = answers or []


class FakePollResultEntry:
    """Заглушка PollAnswerVoters."""

    def __init__(self, option: bytes = b"", voters: int = 0) -> None:
        self.option = option
        self.voters = voters


class FakePollResults:
    """Заглушка PollResults."""

    def __init__(
        self,
        results: list[FakePollResultEntry] | None = None,
        total_voters: int | None = None,
    ) -> None:
        self.results = results or []
        self.total_voters = total_voters


class FakePollMedia:
    """Заглушка message.poll (MessageMediaPoll)."""

    def __init__(
        self,
        poll: FakePoll | None = None,
        results: FakePollResults | None = None,
    ) -> None:
        self.poll = poll
        self.results = results


# ---------------------------------------------------------------------------
# Message entities
# ---------------------------------------------------------------------------

class FakeMessageEntityTextUrl:
    """Заглушка MessageEntityTextUrl.

    Имя класса ВАЖНО — converter.py проверяет type(ent).__name__.
    """

    def __init__(self, offset: int = 0, length: int = 0, url: str = "") -> None:
        self.offset = offset
        self.length = length
        self.url = url


class FakeMessageEntityUrl:
    """Заглушка MessageEntityUrl.

    Имя класса ВАЖНО — converter.py проверяет type(ent).__name__.
    """

    def __init__(self, offset: int = 0, length: int = 0) -> None:
        self.offset = offset
        self.length = length


# ---------------------------------------------------------------------------
# Message (центральный класс)
# ---------------------------------------------------------------------------

class FakeMessage:
    """Заглушка Telethon Message.

    Содержит все поля, читаемые production-кодом (converter.py,
    export_orchestrator.py, media_downloader.py).
    """

    def __init__(
        self,
        id: int = 0,
        date: datetime | None = None,
        out: bool = False,
        message: str = "",
        raw_text: str | None = None,
        sender: FakeUser | None = None,
        sender_id: int | None = None,
        action: FakeAction | None = None,
        reply_to: FakeReplyTo | None = None,
        reply_to_msg_id: int | None = None,
        views: int | None = None,
        forwards: int | None = None,
        fwd_from: FakeFwdFrom | None = None,
        reactions: FakeReactions | None = None,
        poll: FakePollMedia | None = None,
        entities: list[Any] | None = None,
        # media flags
        sticker: Any | None = None,
        photo: Any | None = None,
        voice: Any | None = None,
        video_note: Any | None = None,
        video: Any | None = None,
        audio: Any | None = None,
        gif: Any | None = None,
        document: Any | None = None,
    ) -> None:
        self.id = id
        self.date = date
        self.out = out
        self.message = message
        self.raw_text = raw_text if raw_text is not None else message
        self.sender = sender
        self.sender_id = sender_id
        self.action = action
        self.reply_to = reply_to
        self.reply_to_msg_id = reply_to_msg_id
        self.views = views
        self.forwards = forwards
        self.fwd_from = fwd_from
        self.reactions = reactions
        self.poll = poll
        self.entities = entities
        self.sticker = sticker
        self.photo = photo
        self.voice = voice
        self.video_note = video_note
        self.video = video
        self.audio = audio
        self.gif = gif
        self.document = document

    def download_media(self, file: str | Path, progress_callback: Any = None) -> str | None:
        """Имитация download_media. Создаёт пустой файл, вызывает callback."""
        path = Path(file) if not isinstance(file, Path) else file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        if progress_callback:
            progress_callback(1, 1)
        return str(path)
