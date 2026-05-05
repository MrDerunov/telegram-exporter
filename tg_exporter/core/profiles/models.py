from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class Profile:
    phone: str
    display_name: str = ""
    api_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


def _session_key(api_id: str, phone: str) -> str:
    return f"{api_id}:session:{phone}"


def _normalize_phone(phone: str) -> str:
    phone = (phone or "").strip()
    if not phone:
        return ""
    # Оставляем только `+` в начале и цифры
    digits = "".join(c for c in phone if c.isdigit())
    if phone.startswith("+"):
        return "+" + digits
    return digits
