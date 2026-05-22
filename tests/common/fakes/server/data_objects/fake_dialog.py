"""Заглушка Telethon Dialog.

Поля, читаемые кодом: .id, .name, .title, .entity (с .username, .broadcast),
.is_user, .is_group, .is_channel, .message (.date), .folder (.title).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .fake_user import FakeUser
from .fake_chat import FakeChat
from .fake_folder import FakeFolder

if TYPE_CHECKING:
    from .fake_message import FakeMessage


class FakeDialog:
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
