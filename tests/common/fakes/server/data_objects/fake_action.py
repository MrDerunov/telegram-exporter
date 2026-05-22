"""Заглушка message.action (MessageActionTopicEdit и др.)."""

from __future__ import annotations


class FakeAction:
    def __init__(self, title: str | None = None) -> None:
        self.title = title
