"""
PollAnswer, PollData — представление опросов Telegram.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PollAnswer:
    text: str
    voters: int | None

    def to_dict(self) -> dict:
        return {"text": self.text, "voters": self.voters}


@dataclass(frozen=True)
class PollData:
    question: str
    answers: tuple[PollAnswer, ...]
    total_voters: int | None

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answers": [a.to_dict() for a in self.answers],
            "total_voters": self.total_voters,
        }
