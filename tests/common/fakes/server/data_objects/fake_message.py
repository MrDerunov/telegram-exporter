"""Заглушка Telethon Message.

Содержит все поля, читаемые production-кодом (converter.py,
export_orchestrator.py, media_downloader.py).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .fake_user import FakeUser
    from .fake_action import FakeAction
    from .fake_reply_to import FakeReplyTo
    from .fake_fwd_from import FakeFwdFrom
    from .fake_reactions import FakeReactions
    from .fake_poll import FakePollMedia


class FakeMessage:
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
