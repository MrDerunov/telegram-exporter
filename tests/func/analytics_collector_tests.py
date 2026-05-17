"""Tests for AnalyticsCollector."""
import pytest

from tg_exporter.services.export.models.export_message import ExportMessage


def _msg(**kw) -> ExportMessage:
    defaults = dict(id=1, type="message", date="2024-06-15T10:00:00+00:00", text="Hello")
    defaults.update(kw)
    return ExportMessage(**defaults)


class TestAnalyticsCollector:

    @staticmethod
    def _collect(items):
        """items: list of (msg, is_outgoing)"""
        from tg_exporter.services.export.analytics import AnalyticsCollector
        c = AnalyticsCollector()
        for msg, is_out in items:
            c.add(msg, msg.text or "", is_out)
        return c.result()

    def should_return_empty_result_when_no_messages(self):
        """Пустой коллектор возвращает пустой результат."""
        result = self._collect([])
        assert result.authors == []
        assert result.activity == {}

    def should_count_messages_for_single_author(self):
        """Сообщения одного автора корректно подсчитываются."""
        msgs = [(_msg(id=i, from_id=10, from_name="Alice"), False) for i in range(1, 4)]
        result = self._collect(msgs)
        assert len(result.authors) == 1
        assert result.authors[0].message_count == 3
        assert result.authors[0].name == "Alice"

    def should_sort_authors_by_message_count(self):
        """Авторы сортируются по убыванию количества сообщений."""
        items = (
            [(_msg(id=i, from_id=10, from_name="A"), False) for i in range(1, 6)] +
            [(_msg(id=i + 10, from_id=20, from_name="B"), False) for i in range(1, 3)]
        )
        result = self._collect(items)
        assert result.authors[0].user_id == 10
        assert result.authors[1].user_id == 20

    def should_exclude_outgoing_messages_from_authors(self):
        """Исходящие сообщения исключаются из списка авторов."""
        items = [(_msg(id=1, from_id=10, from_name="Me"), True)]
        result = self._collect(items)
        assert result.authors == []

    def should_count_activity_by_date(self):
        """Активность группируется по датам."""
        items = [
            (_msg(id=1, date="2024-06-15T10:00:00"), False),
            (_msg(id=2, date="2024-06-15T12:00:00"), False),
            (_msg(id=3, date="2024-06-16T08:00:00"), False),
        ]
        result = self._collect(items)
        assert result.activity.get("2024-06-15") == 2
        assert result.activity.get("2024-06-16") == 1

    def should_capture_username(self):
        """Username автора сохраняется."""
        msg = _msg(id=1, from_id=5, from_name="Bob", from_username="bob_tg")
        result = self._collect([(msg, False)])
        assert result.authors[0].username == "bob_tg"

    def should_store_messages_for_author(self):
        """Сообщения сохраняются в статистике автора."""
        msg = _msg(id=1, from_id=7, from_name="Eve", text="Test content")
        result = self._collect([(msg, False)])
        assert len(result.authors[0].messages) == 1
        assert "Test content" in result.authors[0].messages[0]

    def should_skip_none_from_id(self):
        """Сообщения без from_id пропускаются."""
        msg = _msg(id=1, from_id=None, text="Channel post")
        result = self._collect([(msg, False)])
        assert result.authors == []

    def should_count_outgoing_in_activity(self):
        """Исходящие сообщения учитываются в статистике активности."""
        msg = _msg(id=1, from_id=10, from_name="Me", date="2024-01-01T10:00:00")
        result = self._collect([(msg, True)])
        assert result.activity.get("2024-01-01") == 1
