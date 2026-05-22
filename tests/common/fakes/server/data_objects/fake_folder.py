"""Заглушка dialog.folder."""

from __future__ import annotations


class FakeFolder:
    def __init__(self, id: int = 0, title: str | None = None) -> None:
        self.id = id
        self.title = title
