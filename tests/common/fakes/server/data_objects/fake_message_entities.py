"""Заглушки для MessageEntity (TextUrl, Url).

Имена классов ВАЖНЫ — converter.py проверяет type(ent).__name__.
"""

from __future__ import annotations


class FakeMessageEntityTextUrl:
    """Заглушка MessageEntityTextUrl."""

    def __init__(self, offset: int = 0, length: int = 0, url: str = "") -> None:
        self.offset = offset
        self.length = length
        self.url = url


class FakeMessageEntityUrl:
    """Заглушка MessageEntityUrl."""

    def __init__(self, offset: int = 0, length: int = 0) -> None:
        self.offset = offset
        self.length = length
