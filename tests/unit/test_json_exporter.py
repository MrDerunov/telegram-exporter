"""
Тесты JsonExporter — объединённые из Phase 1 (unittest) и Phase 2 (pytest).
"""
from __future__ import annotations

import json
import os
import pytest

from tg_exporter.services.export.models.export_message import ExportMessage
from tg_exporter.services.export.models.reaction_item import ReactionItem
from tg_exporter.services.export.exporters.json_exporter import JsonExporter


def _msg(**kw) -> ExportMessage:
    defaults = dict(id=1, type="message", date="2024-06-15T10:00:00+00:00", text="Hello")
    defaults.update(kw)
    return ExportMessage(**defaults)


class TestJsonExporter:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.tmpdir = str(tmp_path)

    def _run(self, messages, chat_name="Test Chat", topic_title=None, **kw) -> dict:
        exp = JsonExporter(**kw)
        exp.open(self.tmpdir, chat_name, topic_title)
        for msg in messages:
            exp.write(msg)
        files = exp.finalize()
        assert len(files) == 1
        with open(files[0], encoding="utf-8") as f:
            return json.load(f)

    def test_empty_messages_produces_valid_json(self):
        """Пустой список сообщений — валидный JSON с полем messages."""
        data = self._run([])
        assert data["name"] == "Test Chat"
        assert data["messages"] == []

    def test_single_message_in_json(self):
        """Одно сообщение корректно записывается в JSON."""
        data = self._run([_msg(id=42, text="Привет")])
        assert len(data["messages"]) == 1
        assert data["messages"][0]["id"] == 42
        assert data["messages"][0]["text"] == "Привет"

    def test_multiple_messages_preserve_order(self):
        """Сообщения в JSON сохраняют порядок добавления."""
        msgs = [_msg(id=i, text=f"msg{i}") for i in range(1, 6)]
        data = self._run(msgs)
        ids = [m["id"] for m in data["messages"]]
        assert ids == [1, 2, 3, 4, 5]

    def test_topic_title_appears_in_json_header(self):
        """Если передан topic_title — он попадает в JSON."""
        data = self._run([_msg(id=1)], topic_title="General")
        assert data["topic"] == "General"

    def test_author_name_in_json(self):
        """Имя автора сохраняется в поле from."""
        data = self._run([_msg(id=1, from_name="Serge", from_username="serge")])
        assert data["messages"][0]["from"] == "Serge"
        assert data["messages"][0]["from_username"] == "serge"

    def test_include_views_true(self):
        """include_views=True сохраняет views и forwards."""
        data = self._run([_msg(id=1, views=100, forwards=5)], include_views=True)
        assert data["messages"][0]["views"] == 100
        assert data["messages"][0]["forwards"] == 5

    def test_include_views_false_strips_stats(self):
        """include_views=False удаляет views и forwards."""
        data = self._run([_msg(id=1, views=100, forwards=5)], include_views=False)
        assert "views" not in data["messages"][0]
        assert "forwards" not in data["messages"][0]

    def test_no_utf8_bom(self):
        """В начале JSON-файла нет BOM."""
        exp = JsonExporter()
        exp.open(self.tmpdir, "Chat")
        exp.write(_msg())
        files = exp.finalize()
        with open(files[0], "rb") as f:
            raw = f.read(3)
        assert raw != b"\xef\xbb\xbf"

    def test_unicode_preserved(self):
        """Unicode-символы сохраняются без искажений."""
        data = self._run([_msg(text="Тест: 日本語 🎉")])
        assert data["messages"][0]["text"] == "Тест: 日本語 🎉"

    def test_reactions_serialised(self):
        """Реакции сериализуются в JSON."""
        msg = _msg(id=1, reactions=(ReactionItem(emoji="👍", count=3),))
        data = self._run([msg])
        assert data["messages"][0]["reactions"][0]["emoji"] == "👍"

    def test_finalize_returns_registered_path(self):
        """finalize() возвращает путь к созданному файлу."""
        exp = JsonExporter()
        exp.open(self.tmpdir, "C")
        exp.write(_msg())
        files = exp.finalize()
        assert os.path.isfile(files[0])

    def test_close_without_finalize_leaves_no_crash(self):
        """close() без finalize() не падает."""
        exp = JsonExporter()
        exp.open(self.tmpdir, "C")
        exp.write(_msg())
        exp.close()

    def test_close_writes_valid_json_on_cancellation(self):
        """close() дописывает закрывающие скобки — JSON остаётся валидным."""
        exp = JsonExporter()
        exp.open(self.tmpdir, "Chat")
        exp.write(_msg(id=1))
        exp.close()
        assert len(exp.output_files) == 1
        with open(exp.output_files[0], encoding="utf-8") as f:
            data = json.load(f)
        assert data["name"] == "Chat"
        assert len(data["messages"]) == 1

    def test_context_manager_finalizes_on_success(self):
        """Контекстный менеджер вызывает finalize при успехе."""
        exp = JsonExporter()
        with exp:
            exp.open(self.tmpdir, "Chat")
            exp.write(_msg())
        assert len(exp.output_files) == 1
        assert os.path.isfile(exp.output_files[0])

    def test_context_manager_closes_on_error(self):
        """При исключении __exit__ вызывает close(), не finalize()."""
        exp = JsonExporter()
        try:
            with exp:
                exp.open(self.tmpdir, "Chat")
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert exp._file is None
