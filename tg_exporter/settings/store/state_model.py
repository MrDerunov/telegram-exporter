"""StateModel — состояние приложения (frozen).
Хранится в state.json. Содержит список чатов.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChatEntry:
    """Запись о чате в конфиге."""
    name: str
    id: int


@dataclass(frozen=True)
class StateModel:
    chats: tuple[ChatEntry, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "chats": [
                {"name": c.name, "id": c.id}
                for c in self.chats
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> StateModel:
        chats_raw = data.get("chats", []) or []
        chats = tuple(
            ChatEntry(
                name=str(c.get("name", "")),
                id=int(c.get("id", 0)),
            )
            for c in chats_raw
            if isinstance(c, dict)
        )
        return cls(chats=chats)
