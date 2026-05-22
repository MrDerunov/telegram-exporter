"""StateModel — состояние приложения (frozen).
Хранится в state.json. Содержит профили, активный телефон, список чатов.
Заменяет runtime-поля CliConfig + ProfileManager file I/O.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProfileEntry:
    """DTO профиля для сериализации в state.json."""
    phone: str
    display_name: str = ""
    api_id: str = ""


@dataclass(frozen=True)
class ChatEntry:
    """Запись о чате в конфиге."""
    name: str
    id: int


@dataclass(frozen=True)
class StateModel:
    active_phone: str = ""
    profiles: tuple[ProfileEntry, ...] = field(default_factory=tuple)
    chats: tuple[ChatEntry, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "active_phone": self.active_phone,
            "profiles": [
                {"phone": p.phone, "display_name": p.display_name, "api_id": p.api_id}
                for p in self.profiles
            ],
            "chats": [
                {"name": c.name, "id": c.id}
                for c in self.chats
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> StateModel:
        profiles_raw = data.get("profiles", []) or []
        profiles = tuple(
            ProfileEntry(
                phone=str(p.get("phone", "")),
                display_name=str(p.get("display_name", "")),
                api_id=str(p.get("api_id", "")),
            )
            for p in profiles_raw
            if isinstance(p, dict) and p.get("phone")
        )
        chats_raw = data.get("chats", []) or []
        chats = tuple(
            ChatEntry(
                name=str(c.get("name", "")),
                id=int(c.get("id", 0)),
            )
            for c in chats_raw
            if isinstance(c, dict)
        )
        return cls(
            active_phone=str(data.get("active_phone", "")),
            profiles=profiles,
            chats=chats,
        )
