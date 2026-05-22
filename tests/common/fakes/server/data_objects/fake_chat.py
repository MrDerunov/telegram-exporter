"""Заглушка для dialog.entity (Chat/Channel)."""

from __future__ import annotations


class FakeChat:
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
