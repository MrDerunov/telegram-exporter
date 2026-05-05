"""
ReactionItem — представление реакции на сообщение (emoji + count).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReactionItem:
    emoji: str
    count: int

    def to_dict(self) -> dict:
        return {"emoji": self.emoji, "count": self.count}
