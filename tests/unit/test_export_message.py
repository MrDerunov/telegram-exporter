"""Tests for ExportMessage."""
import dataclasses
import unittest

from tg_exporter.services.export.models.export_message import ExportMessage
from tg_exporter.services.export.models.media_type import MediaType
from tg_exporter.services.export.models.reaction_item import ReactionItem
from tg_exporter.services.export.models.poll_data import PollData, PollAnswer


class TestExportMessage(unittest.TestCase):

    def _make(self, **kw):
        defaults = dict(id=1, type="message", date="2024-06-15T10:00:00+00:00", text="Hello")
        defaults.update(kw)
        return ExportMessage(**defaults)

    def test_to_dict_minimal(self):
        msg = self._make()
        d = msg.to_dict()
        self.assertEqual(d["id"], 1)
        self.assertEqual(d["text"], "Hello")
        self.assertEqual(d["date"], "2024-06-15T10:00:00+00:00")
        self.assertNotIn("links", d)
        self.assertNotIn("reactions", d)

    def test_to_dict_omits_none_fields(self):
        msg = self._make(views=None, forwards=None)
        d = msg.to_dict()
        self.assertNotIn("views", d)
        self.assertNotIn("forwards", d)

    def test_to_dict_includes_views_when_set(self):
        msg = self._make(views=500, forwards=10)
        d = msg.to_dict()
        self.assertEqual(d["views"], 500)
        self.assertEqual(d["forwards"], 10)

    def test_with_transcription_immutable(self):
        msg = self._make()
        msg2 = msg.with_transcription("Привет мир")
        self.assertIsNone(msg.transcription)
        self.assertEqual(msg2.transcription, "Привет мир")

    def test_with_media_immutable(self):
        msg = self._make()
        msg2 = msg.with_media("/path/file.ogg", MediaType.VOICE, "audio/ogg")
        self.assertIsNone(msg.media_path)
        self.assertEqual(msg2.media_path, "/path/file.ogg")
        self.assertEqual(msg2.media_type, MediaType.VOICE)

    def test_frozen_prevents_mutation(self):
        msg = self._make()
        with self.assertRaises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            msg.text = "modified"  # type: ignore[misc]

    def test_reactions_in_to_dict(self):
        msg = ExportMessage(
            id=2, type="message", date="2024-01-01T00:00:00",
            reactions=(ReactionItem(emoji="👍", count=5),),
        )
        d = msg.to_dict()
        self.assertEqual(d["reactions"], [{"emoji": "👍", "count": 5}])

    def test_poll_in_to_dict(self):
        poll = PollData(
            question="Что лучше?",
            answers=(PollAnswer(text="A", voters=10), PollAnswer(text="B", voters=5)),
            total_voters=15,
        )
        msg = ExportMessage(id=3, type="message", date="2024-01-01T00:00:00", poll=poll)
        d = msg.to_dict()
        self.assertEqual(d["poll"]["question"], "Что лучше?")
        self.assertEqual(d["poll"]["total_voters"], 15)
