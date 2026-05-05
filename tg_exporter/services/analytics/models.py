"""
Модели данных для аналитики — AuthorStats и AnalyticsResult.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---- Пределы памяти ----
# Обрезка длинных сообщений и лимит кол-ва сохранённых сообщений на автора
# предотвращают OOM на больших каналах (1M+ сообщений).
_MAX_ENTRY_CHARS = 2000
_MAX_MESSAGES_PER_AUTHOR = 5000


@dataclass
class AuthorStats:
    """Статистика по одному автору."""
    user_id: int
    name: str
    username: str
    message_count: int
    messages: list[str] = field(default_factory=list)  # отформатированные тексты


@dataclass
class AnalyticsResult:
    """Результат сбора аналитики."""
    authors: list[AuthorStats] = field(default_factory=list)   # отсортированы по убыванию
    activity: dict[str, int] = field(default_factory=dict)     # date → count
