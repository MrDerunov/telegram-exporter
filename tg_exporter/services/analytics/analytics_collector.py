"""
AnalyticsCollector — накапливает аналитику по сообщениям по мере их обработки.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Optional

from .author_stats import AuthorStats, _MAX_ENTRY_CHARS, _MAX_MESSAGES_PER_AUTHOR
from .analytics_result import AnalyticsResult
from ..export.export_message import ExportMessage


class AnalyticsCollector:
    """
    Накапливает аналитику по сообщениям по мере их обработки.

    Использование:
        collector = AnalyticsCollector()
        for msg in messages:
            collector.add(msg, formatted_text)
        result = collector.result()
    """

    def __init__(
        self,
        max_entry_chars: int = _MAX_ENTRY_CHARS,
        max_messages_per_author: int = _MAX_MESSAGES_PER_AUTHOR,
    ) -> None:
        self._author_counts: dict[int, int] = {}
        # deque с maxlen сохраняет только последние N сообщений автора — защита от OOM
        self._author_messages: dict[int, Deque[str]] = {}
        self._author_meta: dict[int, dict] = {}
        self._activity: dict[str, int] = {}
        self._max_entry_chars = max_entry_chars
        self._max_messages_per_author = max_messages_per_author

    def add(self, msg: ExportMessage, formatted_text: str, is_outgoing: bool = False) -> None:
        """
        Добавляет сообщение в статистику.

        is_outgoing: исходящие сообщения не учитываются в авторской статистике.
        """
        author_id = msg.from_id
        if not is_outgoing and isinstance(author_id, int) and author_id > 0:
            name = (msg.from_name or "Без имени").strip() or "Без имени"
            username = (msg.from_username or "").strip()

            meta = self._author_meta.get(author_id, {})
            if not meta.get("name") and name:
                meta["name"] = name
            if not meta.get("username") and username:
                meta["username"] = username
            self._author_meta[author_id] = meta

            self._author_counts[author_id] = self._author_counts.get(author_id, 0) + 1

            # Обрезаем длинные сообщения — для аналитики полный текст не нужен
            truncated = formatted_text or ""
            if len(truncated) > self._max_entry_chars:
                truncated = truncated[: self._max_entry_chars].rstrip() + "…"
            entry = truncated
            if msg.id is not None:
                entry = f"ID: {msg.id}\n{truncated}".strip()

            bucket = self._author_messages.get(author_id)
            if bucket is None:
                bucket = deque(maxlen=self._max_messages_per_author)
                self._author_messages[author_id] = bucket
            bucket.append(entry)

        # Активность по дням
        date_key = _date_key(msg.date)
        if date_key:
            self._activity[date_key] = self._activity.get(date_key, 0) + 1

    def result(self) -> AnalyticsResult:
        sorted_authors = sorted(
            self._author_counts.items(), key=lambda x: x[1], reverse=True
        )
        authors = []
        for uid, count in sorted_authors:
            meta = self._author_meta.get(uid, {})
            authors.append(AuthorStats(
                user_id=uid,
                name=meta.get("name", "Без имени"),
                username=meta.get("username", ""),
                message_count=count,
                messages=list(self._author_messages.get(uid, [])),
            ))
        return AnalyticsResult(authors=authors, activity=dict(self._activity))


# ---- Helpers ----

def _date_key(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if "T" in value:
        return value.split("T")[0]
    if " " in value:
        return value.split(" ")[0]
    return value[:10] if len(value) >= 10 else value
