"""
AuthorFilter — фильтр по авторам сообщений в задаче экспорта.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class AuthorFilter:
    """Фильтр по авторам сообщений."""
    user_ids: frozenset[int] = field(default_factory=frozenset)

    @classmethod
    def from_ids(cls, ids: list[int]) -> AuthorFilter:
        return cls(user_ids=frozenset(ids))

    def is_empty(self) -> bool:
        return len(self.user_ids) == 0

    def matches(self, user_id: int | None) -> bool:
        if self.is_empty():
            return True
        return user_id in self.user_ids
