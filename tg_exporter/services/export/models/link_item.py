"""
LinkItem — представление ссылки/URL в сообщении.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LinkItem:
    url: str
    text: str | None = None

    def to_dict(self) -> dict:
        d: dict = {"url": self.url}
        if self.text and self.text != self.url:
            d["text"] = self.text
        return d
