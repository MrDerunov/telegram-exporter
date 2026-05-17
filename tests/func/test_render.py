"""Tests for render_top_authors and render_activity."""
import unittest

from tg_exporter.services.export.analytics import AnalyticsCollector, render_top_authors, render_activity, AnalyticsResult
from tg_exporter.services.export.models.export_message import ExportMessage


def _msg(**kw) -> ExportMessage:
    defaults = dict(id=1, type="message", date="2024-06-15T10:00:00+00:00", text="Hello")
    defaults.update(kw)
    return ExportMessage(**defaults)


class TestRenderTopAuthors(unittest.TestCase):

    def _result(self, msgs_by_author: dict):
        c = AnalyticsCollector()
        for author_id, (name, msgs) in msgs_by_author.items():
            for i, text in enumerate(msgs):
                msg = _msg(id=i, from_id=author_id, from_name=name, text=text)
                c.add(msg, text)
        return c.result()

    def should_return_list_of_strings(self):
        result = self._result({1: ("Alice", ["msg1", "msg2"])})
        parts = render_top_authors(result)
        self.assertIsInstance(parts, list)
        self.assertGreater(len(parts), 0)
        self.assertIsInstance(parts[0], str)

    def should_contain_author_name(self):
        result = self._result({1: ("Alice", ["hi"])})
        parts = render_top_authors(result)
        combined = "".join(parts)
        self.assertIn("Alice", combined)

    def should_contain_message_count(self):
        result = self._result({1: ("Alice", ["a", "b", "c"])})
        parts = render_top_authors(result)
        combined = "".join(parts)
        self.assertIn("3", combined)

    def should_return_empty_list_for_empty_result(self):
        parts = render_top_authors(AnalyticsResult())
        self.assertEqual(parts, [])

    def should_split_into_multiple_parts_when_exceeding_word_limit(self):
        """With tiny word limit, multiple authors should produce multiple parts."""
        result = self._result({
            1: ("Alice", ["word " * 20] * 5),
            2: ("Bob", ["word " * 20] * 5),
        })
        parts = render_top_authors(result, words_per_file=30)
        self.assertGreater(len(parts), 1)


class TestRenderActivity(unittest.TestCase):

    def should_return_empty_string_for_empty_result(self):
        result = AnalyticsResult()
        self.assertEqual(render_activity(result), "")

    def should_contain_date_and_count(self):
        result = AnalyticsResult(activity={"2024-06-15": 5})
        out = render_activity(result)
        self.assertIn("2024-06-15", out)
        self.assertIn("5", out)

    def should_sort_dates(self):
        result = AnalyticsResult(activity={"2024-06-20": 2, "2024-06-10": 7})
        out = render_activity(result)
        self.assertLess(out.index("2024-06-10"), out.index("2024-06-20"))

    def should_contain_weekday_name(self):
        result = AnalyticsResult(activity={"2024-06-17": 3})  # Monday
        out = render_activity(result)
        self.assertIn("Понедельник", out)

    def should_contain_hot_days_section(self):
        result = AnalyticsResult(activity={"2024-06-15": 100, "2024-06-16": 5})
        out = render_activity(result)
        self.assertIn("горячие", out.lower())
