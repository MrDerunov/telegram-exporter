"""Хранилище фейковых сообщений.

Сообщения индексируются по peer_id и сортируются по id.
"""

from __future__ import annotations

from datetime import datetime

from ..data_objects.fake_message import FakeMessage


class MessageStore:
    def __init__(self) -> None:
        self._messages: dict[int, list[FakeMessage]] = {}

    def add_messages(self, peer_id: int, messages: list[FakeMessage]) -> None:
        existing = self._messages.setdefault(peer_id, [])
        existing.extend(messages)
        existing.sort(key=lambda m: m.id)

    def add_message(self, peer_id: int, message: FakeMessage) -> None:
        self.add_messages(peer_id, [message])

    def get_messages(self, peer_id: int) -> list[FakeMessage]:
        return list(self._messages.get(peer_id, []))

    def query(
        self,
        peer_id: int,
        min_id: int = 0,
        offset_date: datetime | None = None,
        limit: int | None = None,
        reply_to: int | None = None,
    ) -> list[FakeMessage]:
        """Выбрать сообщения с фильтрацией (как iter_messages).

        Возвращает сообщения от новых к старым (как Telethon iter_messages).
        """
        messages = self._messages.get(peer_id, [])
        # Сначала от новых к старым (как Telethon) — сортируем по дате (убывание)
        messages = sorted(
            messages,
            key=lambda m: m.date if m.date is not None else datetime.min,
            reverse=True,
        )
        filtered = [m for m in messages if m.id > min_id]
        if offset_date is not None:
            # Telethon: offset_date — сообщения СТАРШЕ этой даты (date < offset_date)
            filtered = [
                m for m in filtered
                if m.date is not None and m.date < offset_date
            ]
        if reply_to is not None:
            filtered = [
                m for m in filtered
                if getattr(m, "reply_to_msg_id", None) == reply_to
            ]
        if limit is not None:
            filtered = filtered[:limit]
        return filtered

    def count(
        self,
        peer_id: int,
        min_id: int = 0,
        offset_date: datetime | None = None,
        reply_to: int | None = None,
    ) -> int:
        """Количество сообщений после фильтрации."""
        messages = self._messages.get(peer_id, [])
        filtered = [m for m in messages if m.id > min_id]
        if offset_date is not None:
            # Telethon: offset_date — сообщения СТАРШЕ этой даты (date < offset_date)
            filtered = [
                m for m in filtered
                if m.date is not None and m.date < offset_date
            ]
        if reply_to is not None:
            filtered = [
                m for m in filtered
                if getattr(m, "reply_to_msg_id", None) == reply_to
            ]
        return len(filtered)

    def clear(self) -> None:
        self._messages.clear()
