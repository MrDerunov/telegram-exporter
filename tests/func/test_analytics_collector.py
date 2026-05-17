"""Tests for AnalyticsCollector."""
import unittest

from tg_exporter.services.export.models.export_message import ExportMessage


def _msg(**kw) -> ExportMessage:
    defaults = dict(id=1, type="message", date="2024-06-15T10:00:00+00:00", text="Hello")
    defaults.update(kw)
    return ExportMessage(**defaults)


class TestAnalyticsCollector(unittest.TestCase):

    def setUp(self):
        from tg_exporter.services.export.analytics import AnalyticsCollector
        self.AnalyticsCollector = AnalyticsCollector

    def _collect(self, items):
        """items: list of (msg, is_outgoing)"""
        c = self.AnalyticsCollector()
        for msg, is_out in items:
            c.add(msg, msg.text or "", is_out)
        return c.result()

    def test_empty_result(self):
        result = self._collect([])
        self.assertEqual(result.authors, [])
        self.assertEqual(result.activity, {})

    def test_single_author_count(self):
        msgs = [(_msg(id=i, from_id=10, from_name="Alice"), False) for i in range(1, 4)]
        result = self._collect(msgs)
        self.assertEqual(len(result.authors), 1)
        self.assertEqual(result.authors[0].message_count, 3)
        self.assertEqual(result.authors[0].name, "Alice")

    def test_multiple_authors_sorted_by_count(self):
        items = (
            [(_msg(id=i, from_id=10, from_name="A"), False) for i in range(1, 6)] +
            [(_msg(id=i + 10, from_id=20, from_name="B"), False) for i in range(1, 3)]
        )
        result = self._collect(items)
        self.assertEqual(result.authors[0].user_id, 10)  # more messages
        self.assertEqual(result.authors[1].user_id, 20)

    def test_outgoing_messages_excluded_from_authors(self):
        items = [(_msg(id=1, from_id=10, from_name="Me"), True)]
        result = self._collect(items)
        self.assertEqual(result.authors, [])

    def test_activity_by_date(self):
        items = [
            (_msg(id=1, date="2024-06-15T10:00:00"), False),
            (_msg(id=2, date="2024-06-15T12:00:00"), False),
            (_msg(id=3, date="2024-06-16T08:00:00"), False),
        ]
        result = self._collect(items)
        self.assertEqual(result.activity.get("2024-06-15"), 2)
        self.assertEqual(result.activity.get("2024-06-16"), 1)

    def test_username_captured(self):
        msg = _msg(id=1, from_id=5, from_name="Bob", from_username="bob_tg")
        result = self._collect([(msg, False)])
        self.assertEqual(result.authors[0].username, "bob_tg")

    def test_messages_stored(self):
        msg = _msg(id=1, from_id=7, from_name="Eve", text="Test content")
        result = self._collect([(msg, False)])
        self.assertEqual(len(result.authors[0].messages), 1)
        self.assertIn("Test content", result.authors[0].messages[0])

    def test_none_from_id_skipped(self):
        msg = _msg(id=1, from_id=None, text="Channel post")
        result = self._collect([(msg, False)])
        self.assertEqual(result.authors, [])

    def test_activity_outgoing_still_counted(self):
        """Outgoing messages should still count for activity tracking."""
        msg = _msg(id=1, from_id=10, from_name="Me", date="2024-01-01T10:00:00")
        result = self._collect([(msg, True)])
        self.assertEqual(result.activity.get("2024-01-01"), 1)
