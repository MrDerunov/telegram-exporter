"""Тесты конвертера Telethon → ExportMessage."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from tg_exporter.services.telegram import (
    message_to_export,
    _normalize,
    _build_forwarded_from,
    _build_reactions,
    _build_poll,
    _extract_links,
    _detect_media_type,
)
from tg_exporter.services.export.models.export_message import ExportMessage
from tg_exporter.services.export.models.media_type import MediaType
from tests.common.fakes.factories import generate_messages


# ---------------------------------------------------------------------------
# Helpers: build Telethon-like message objects
# ---------------------------------------------------------------------------

def _make_msg(**overrides) -> object:
    """Создаёт объект, похожий на Telethon Message."""
    defaults = dict(
        id=1,
        date=datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc),
        message="Hello world",
        raw_text=None,
        sender=None,
        sender_id=None,
        action=None,
        reply_to=None,
        reply_to_msg_id=None,
        views=None,
        forwards=None,
        fwd_from=None,
        reactions=None,
        poll=None,
        photo=None,
        video=None,
        voice=None,
        video_note=None,
        audio=None,
        gif=None,
        document=None,
        sticker=None,
        entities=None,
    )
    defaults.update(overrides)
    return type("FakeMessage", (), defaults)()


def _make_sender(name="John", username="john123"):
    """Создаёт объект-отправителя."""
    d = type("FakeSender", (), {"first_name": name, "last_name": None, "username": username})()
    return d


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------

class TestNormalize:
    def should_return_empty_string_when_none(self):
        assert _normalize(None) == ""

    def should_passthrough_string(self):
        assert _normalize("Hello") == "Hello"

    def should_extract_text_from_object(self):
        obj = type("HasText", (), {"text": "indirect"})()
        assert _normalize(obj) == "indirect"

    def should_return_str_representation_when_no_text(self):
        obj = type("NoText", (), {})()
        # str(obj) will be something like <...>
        result = _normalize(obj)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _build_forwarded_from
# ---------------------------------------------------------------------------

class TestBuildForwardedFrom:
    def should_return_none_when_none(self):
        assert _build_forwarded_from(None) is None

    def should_return_none_when_falsy_object(self):
        fwd = type("Fwd", (), {"from_name": None, "from_id": None})()
        assert _build_forwarded_from(fwd) is None

    def should_return_from_name(self):
        fwd = type("Fwd", (), {"from_name": "Alice", "from_id": None})()
        assert _build_forwarded_from(fwd) == "Alice"

    def should_return_from_id_when_no_name(self):
        fwd = type("Fwd", (), {"from_name": None, "from_id": 777})()
        assert _build_forwarded_from(fwd) == "from_id:777"

    def should_return_channel_post(self):
        fwd = type("Fwd", (), {"from_name": None, "from_id": None, "channel_post": 42})()
        assert _build_forwarded_from(fwd) == "channel_post:42"

    def should_prioritize_name_over_id(self):
        fwd = type("Fwd", (), {"from_name": "Bob", "from_id": 999})()
        assert _build_forwarded_from(fwd) == "Bob"


# ---------------------------------------------------------------------------
# _build_reactions
# ---------------------------------------------------------------------------

class TestBuildReactions:
    def should_return_empty_list_when_reactions_is_none(self):
        msg = _make_msg(reactions=None)
        assert _build_reactions(msg) == []

    def should_return_empty_list_when_no_results_attr(self):
        reactions = type("NoResults", (), {})()
        assert _build_reactions(type("M", (), {"reactions": reactions})()) == []

    def should_return_empty_list_when_results_empty(self):
        reactions = type("RE", (), {"results": []})()
        assert _build_reactions(type("M", (), {"reactions": reactions})()) == []

    def should_build_reactions_with_emoticon(self):
        reaction = type("R", (), {"emoticon": "👍"})()
        result = type("Res", (), {"reaction": reaction, "count": 3})()
        reactions = type("RE", (), {"results": [result]})()
        items = _build_reactions(type("M", (), {"reactions": reactions})())
        assert len(items) == 1
        assert items[0].emoji == "👍"
        assert items[0].count == 3

    def should_fallback_to_str_when_no_emoticon(self):
        reaction = type("R", (), {"emoticon": None, "__str__": lambda s: "custom"})()
        result = type("Res", (), {"reaction": reaction, "count": 1})()
        reactions = type("RE", (), {"results": [result]})()
        items = _build_reactions(type("M", (), {"reactions": reactions})())
        assert items[0].emoji == "custom"


# ---------------------------------------------------------------------------
# _build_poll
# ---------------------------------------------------------------------------

class TestBuildPoll:
    def should_return_none_when_no_poll(self):
        assert _build_poll(_make_msg(poll=None)) is None

    def should_return_none_when_poll_without_inner(self):
        media = type("MP", (), {"poll": None})()
        assert _build_poll(_make_msg(poll=media)) is None

    def should_build_simple_poll(self):
        answer = type("A", (), {"option": b"0", "text": "Yes"})()
        inner = type("P", (), {"question": "Q?", "answers": [answer]})()
        media = type("MP", (), {"poll": inner, "results": None})()
        poll = _build_poll(_make_msg(poll=media))
        assert poll is not None
        assert poll.question == "Q?"
        assert len(poll.answers) == 1
        assert poll.answers[0].text == "Yes"
        assert poll.answers[0].voters is None

    def should_build_poll_with_results(self):
        answer = type("A", (), {"option": b"0", "text": "A"})()
        inner = type("P", (), {"question": "Q?", "answers": [answer]})()
        res_entry = type("RE", (), {"option": b"0", "voters": 5})()
        results = type("RR", (), {"results": [res_entry], "total_voters": 5})()
        media = type("MP", (), {"poll": inner, "results": results})()
        poll = _build_poll(_make_msg(poll=media))
        assert poll.answers[0].voters == 5
        assert poll.total_voters == 5


# ---------------------------------------------------------------------------
# _extract_links
# ---------------------------------------------------------------------------

class TestExtractLinks:
    def should_return_empty_list_when_no_entities(self):
        assert _extract_links(_make_msg(entities=None)) == []

    def should_extract_message_entity_text_url(self):
        raw = "click here"
        ent = type("MessageEntityTextUrl", (), {
            "offset": 0,
            "length": 5,
            "url": "https://example.com",
        })()
        msg = _make_msg(entities=[ent], raw_text=raw)
        links = _extract_links(msg)
        assert len(links) == 1
        assert links[0].url == "https://example.com"
        assert links[0].text == "click"

    def should_set_text_none_when_label_equals_url(self):
        raw = "https://example.com"
        ent = type("MessageEntityTextUrl", (), {
            "offset": 0,
            "length": len(raw),
            "url": "https://example.com",
        })()
        msg = _make_msg(entities=[ent], raw_text=raw)
        links = _extract_links(msg)
        assert links[0].text is None  # label == url → не дублируем

    def should_extract_message_entity_url(self):
        raw = "https://openai.com"
        ent = type("MessageEntityUrl", (), {
            "offset": 0,
            "length": len(raw),
        })()
        msg = _make_msg(entities=[ent], raw_text=raw)
        links = _extract_links(msg)
        assert links[0].url == "https://openai.com"

    def should_deduplicate_by_url(self):
        raw = "a b"
        ent1 = type("MessageEntityTextUrl", (), {"offset": 0, "length": 1, "url": "https://x.com"})()
        ent2 = type("MessageEntityTextUrl", (), {"offset": 2, "length": 1, "url": "https://x.com"})()
        msg = _make_msg(entities=[ent1, ent2], raw_text=raw)
        links = _extract_links(msg)
        assert len(links) == 1


# ---------------------------------------------------------------------------
# _detect_media_type
# ---------------------------------------------------------------------------

class TestDetectMediaType:
    def should_return_none_when_no_media(self):
        assert _detect_media_type(_make_msg()) is None

    def should_detect_photo(self):
        assert _detect_media_type(_make_msg(photo=True)) == MediaType.PHOTO

    def should_detect_video(self):
        assert _detect_media_type(_make_msg(video=True)) == MediaType.VIDEO

    def should_detect_voice(self):
        assert _detect_media_type(_make_msg(voice=True)) == MediaType.VOICE

    def should_detect_video_note(self):
        assert _detect_media_type(_make_msg(video_note=True)) == MediaType.VIDEO_NOTE

    def should_detect_audio(self):
        assert _detect_media_type(_make_msg(audio=True)) == MediaType.AUDIO

    def should_detect_animation(self):
        assert _detect_media_type(_make_msg(gif=True)) == MediaType.ANIMATION

    def should_detect_document(self):
        assert _detect_media_type(_make_msg(document=True)) == MediaType.DOCUMENT

    def should_detect_sticker(self):
        assert _detect_media_type(_make_msg(sticker=True)) == MediaType.STICKER

    def should_prioritize_sticker_over_photo(self):
        assert _detect_media_type(_make_msg(sticker=True, photo=True)) == MediaType.STICKER


# ---------------------------------------------------------------------------
# message_to_export — интеграционные тесты
# ---------------------------------------------------------------------------

class TestMessageToExport:
    def should_convert_basic_message(self):
        """Конвертация базового сообщения."""
        msg = generate_messages(1)[0]
        export = message_to_export(msg)
        assert export.id == 1
        assert export.text == "Test message #1"
        assert export.type == "message"

    def should_set_type_to_service_when_action_present(self):
        msg = _make_msg(action="some_action")
        export = message_to_export(msg)
        assert export.type == "service"

    def should_extract_from_username(self):
        msg = _make_msg(sender=_make_sender("John", "john123"))
        export = message_to_export(msg)
        # from_name зависит от get_display_name (Telethon), фейковый sender не совместим
        # from_username извлекается через простой getattr
        assert export.from_username == "john123"

    def should_extract_sender_id(self):
        msg = _make_msg(sender_id=777)
        export = message_to_export(msg)
        assert export.from_id == 777

    def should_format_date_as_iso(self):
        dt = datetime(2024, 1, 15, 12, 30, tzinfo=timezone.utc)
        msg = _make_msg(date=dt)
        export = message_to_export(msg)
        assert export.date == "2024-01-15T12:30:00+00:00"

    def should_produce_empty_string_when_date_is_none(self):
        msg = _make_msg(date=None)
        export = message_to_export(msg)
        assert export.date == ""

    def should_extract_reply_to_message_id(self):
        msg = _make_msg(reply_to_msg_id=42)
        export = message_to_export(msg)
        assert export.reply_to_message_id == 42

    def should_extract_views_and_forwards(self):
        msg = _make_msg(views=500, forwards=10)
        export = message_to_export(msg)
        assert export.views == 500
        assert export.forwards == 10

    def should_extract_forwarded_from(self):
        fwd = type("Fwd", (), {"from_name": "Alice", "from_id": None})()
        msg = _make_msg(fwd_from=fwd)
        export = message_to_export(msg)
        assert export.forwarded_from == "Alice"

    def should_extract_topic_from_reply_to_top_msg_id(self):
        reply = type("R", (), {"top_msg_id": 100, "reply_to_top_id": None, "forum_topic": None})()
        msg = _make_msg(reply_to=reply)
        export = message_to_export(msg)
        assert export.topic_id == 100
        assert export.is_topic_message is True

    def should_extract_topic_from_reply_to_top_id(self):
        reply = type("R", (), {"top_msg_id": None, "reply_to_top_id": 200, "forum_topic": None})()
        msg = _make_msg(reply_to=reply)
        export = message_to_export(msg)
        assert export.topic_id == 200

    def should_detect_forum_topic_as_true(self):
        reply = type("R", (), {"top_msg_id": 1, "forum_topic": True})()
        msg = _make_msg(reply_to=reply)
        export = message_to_export(msg)
        assert export.is_forum_topic is True

    def should_detect_forum_topic_as_false(self):
        reply = type("R", (), {"top_msg_id": 1, "forum_topic": False})()
        msg = _make_msg(reply_to=reply)
        export = message_to_export(msg)
        assert export.is_forum_topic is False

    def should_extract_topic_title_from_action(self):
        action = type("A", (), {"title": "General"})()
        msg = _make_msg(action=action)
        export = message_to_export(msg)
        assert export.topic_title == "General"

    def should_extract_reactions_in_export(self):
        reaction = type("R", (), {"emoticon": "👍"})()
        result = type("Res", (), {"reaction": reaction, "count": 7})()
        reactions = type("RE", (), {"results": [result]})()
        msg = _make_msg(reactions=reactions)
        export = message_to_export(msg)
        assert len(export.reactions) == 1
        assert export.reactions[0].emoji == "👍"
        assert export.reactions[0].count == 7

    def should_detect_media_type_in_export(self):
        msg = _make_msg(photo=True)
        export = message_to_export(msg)
        assert export.media_type == MediaType.PHOTO

    def should_prioritize_raw_text_over_message(self):
        msg = _make_msg(message="fallback", raw_text="actual")
        export = message_to_export(msg)
        assert export.text == "actual"

    def should_fallback_to_message_when_no_raw_text(self):
        msg = _make_msg(message="only", raw_text=None)
        export = message_to_export(msg)
        assert export.text == "only"

    def should_extract_poll_in_export(self):
        answer = type("A", (), {"option": b"0", "text": "Да"})()
        inner = type("P", (), {"question": "?", "answers": [answer]})()
        media = type("MP", (), {"poll": inner, "results": None})()
        msg = _make_msg(poll=media)
        export = message_to_export(msg)
        assert export.poll is not None
        assert export.poll.question == "?"

    def should_return_correct_structure_for_empty_message(self):
        msg = _make_msg(id=0, message="", date=datetime(2024, 1, 1, tzinfo=timezone.utc))
        export = message_to_export(msg)
        assert isinstance(export, ExportMessage)
        assert export.id == 0
        assert export.type == "message"
        assert export.text == ""

    def should_extract_links_in_export(self):
        raw = "click here"
        ent = type("MessageEntityTextUrl", (), {
            "offset": 0,
            "length": 5,
            "url": "https://example.com",
        })()
        msg = _make_msg(entities=[ent], raw_text=raw)
        export = message_to_export(msg)
        assert len(export.links) == 1
        assert export.links[0].url == "https://example.com"
