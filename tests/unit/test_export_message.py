"""Tests for ExportMessage."""
import dataclasses

import pytest

from tg_exporter.services.export.models.export_message import ExportMessage
from tg_exporter.services.export.models.media_type import MediaType
from tg_exporter.services.export.models.reaction_item import ReactionItem
from tg_exporter.services.export.models.poll_data import PollData, PollAnswer


class TestExportMessage:

    def _make(self, **kw):
        defaults = dict(id=1, type="message", date="2024-06-15T10:00:00+00:00", text="Hello")
        defaults.update(kw)
        return ExportMessage(**defaults)

    def test_convert_to_dict_with_minimal_fields(self):
        msg = self._make()
        d = msg.to_dict()
        assert d["id"] == 1
        assert d["text"] == "Hello"
        assert d["date"] == "2024-06-15T10:00:00+00:00"
        assert "links" not in d
        assert "reactions" not in d

    def test_omit_none_fields_in_to_dict(self):
        msg = self._make(views=None, forwards=None)
        d = msg.to_dict()
        assert "views" not in d
        assert "forwards" not in d

    def test_include_views_when_set(self):
        msg = self._make(views=500, forwards=10)
        d = msg.to_dict()
        assert d["views"] == 500
        assert d["forwards"] == 10

    def test_return_new_instance_with_transcription(self):
        msg = self._make()
        msg2 = msg.with_transcription("Привет мир")
        assert msg.transcription is None
        assert msg2.transcription == "Привет мир"

    def test_return_new_instance_with_media(self):
        msg = self._make()
        msg2 = msg.with_media("/path/file.ogg", MediaType.VOICE, "audio/ogg")
        assert msg.media_path is None
        assert msg2.media_path == "/path/file.ogg"
        assert msg2.media_type == MediaType.VOICE

    def test_prevent_mutation_as_frozen(self):
        msg = self._make()
        with pytest.raises(Exception):
            msg.text = "modified"  # type: ignore[misc]

    def test_serialize_reactions_in_to_dict(self):
        msg = ExportMessage(
            id=2, type="message", date="2024-01-01T00:00:00",
            reactions=(ReactionItem(emoji="👍", count=5),),
        )
        d = msg.to_dict()
        assert d["reactions"] == [{"emoji": "👍", "count": 5}]

    def test_serialize_poll_in_to_dict(self):
        poll = PollData(
            question="Что лучше?",
            answers=(PollAnswer(text="A", voters=10), PollAnswer(text="B", voters=5)),
            total_voters=15,
        )
        msg = ExportMessage(id=3, type="message", date="2024-01-01T00:00:00", poll=poll)
        d = msg.to_dict()
        assert d["poll"]["question"] == "Что лучше?"
        assert d["poll"]["total_voters"] == 15
