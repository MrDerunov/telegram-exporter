"""Заглушка Telethon User (и совместимость с Chat/Channel).

converter.py вызывает get_display_name(message.sender), который читает
.first_name, .last_name (User) или .title (Chat/Channel).
"""

from __future__ import annotations


class FakeUser:
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
