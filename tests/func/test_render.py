"""Tests for render_top_authors and render_activity."""
import pytest

from tg_exporter.services.export.analytics import AnalyticsCollector, render_top_authors, render_activity, AnalyticsResult
from tg_exporter.services.export.models.export_message import ExportMessage


def _msg(**kw) -> ExportMessage:
    defaults = dict(id=1, type="message", date="2024-06-15T10:00:00+00:00", text="Hello")
    defaults.update(kw)
    return ExportMessage(**defaults)


class TestRenderTopAuthors:

    @staticmethod
    def _result(msgs_by_author: dict):
        c = AnalyticsCollector()
        for author_id, (name, msgs) in msgs_by_author.items():
            for i, text in enumerate(msgs):
                msg = _msg(id=i, from_id=author_id, from_name=name, text=text)
                c.add(msg, text)
        return c.result()

    def test_return_list_of_strings(self):
        """Результат — список строк."""
        result = self._result({1: ("Alice", ["msg1", "msg2"])})
        parts = render_top_authors(result)
        assert isinstance(parts, list)
        assert len(parts) > 0
        assert isinstance(parts[0], str)

    def test_contain_author_name(self):
        """Вывод содержит имя автора."""
        result = self._result({1: ("Alice", ["hi"])})
        parts = render_top_authors(result)
        combined = "".join(parts)
        assert "Alice" in combined

    def test_contain_message_count(self):
        """Вывод содержит количество сообщений."""
        result = self._result({1: ("Alice", ["a", "b", "c"])})
        parts = render_top_authors(result)
        combined = "".join(parts)
        assert "3" in combined

    def test_return_empty_list_for_empty_result(self):
        """Пустой результат — пустой список."""
        parts = render_top_authors(AnalyticsResult())
        assert parts == []

    def test_split_into_multiple_parts_when_exceeding_word_limit(self):
        """При превышении лимита слов вывод разбивается на части."""
        result = self._result({
            1: ("Alice", ["word " * 20] * 5),
            2: ("Bob", ["word " * 20] * 5),
        })
        parts = render_top_authors(result, words_per_file=30)
        assert len(parts) > 1


class TestRenderActivity:

    def test_return_empty_string_for_empty_result(self):
        """Пустой результат — пустая строка."""
        assert render_activity(AnalyticsResult()) == ""

    def test_contain_date_and_count(self):
        """Вывод содержит дату и количество."""
        result = AnalyticsResult(activity={"2024-06-15": 5})
        out = render_activity(result)
        assert "2024-06-15" in out
        assert "5" in out

    def test_sort_dates(self):
        """Даты сортируются по возрастанию."""
        result = AnalyticsResult(activity={"2024-06-20": 2, "2024-06-10": 7})
        out = render_activity(result)
        assert out.index("2024-06-10") < out.index("2024-06-20")

    def test_contain_weekday_name(self):
        """Вывод содержит день недели на русском."""
        result = AnalyticsResult(activity={"2024-06-17": 3})
        out = render_activity(result)
        assert "Понедельник" in out

    def test_contain_hot_days_section(self):
        """Вывод содержит раздел с горячими днями."""
        result = AnalyticsResult(activity={"2024-06-15": 100, "2024-06-16": 5})
        out = render_activity(result)
        assert "горячие" in out.lower()
