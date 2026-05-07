"""
Тесты экспортеров — JsonExporter и MarkdownExporter.

Проверяют реальные сигнатуры классов и методов из:
- tg_exporter/services/export/exporters/json_exporter.py
- tg_exporter/services/export/exporters/markdown_exporter.py
- tg_exporter/services/export/export_message.py
"""

from __future__ import annotations

import json
import os
import tempfile
import pytest

from tg_exporter.services.export.export_message import ExportMessage
from tg_exporter.services.export.exporters.json_exporter import JsonExporter
from tg_exporter.services.export.exporters.markdown_exporter import MarkdownExporter
from tg_exporter.services.export.markdown_settings import MarkdownSettings


def _msg(**kw) -> ExportMessage:
    defaults = dict(id=1, type="message", date="2024-06-15T10:00:00+00:00", text="Hello")
    defaults.update(kw)
    return ExportMessage(**defaults)


class TestJsonExporter:
    """Тесты JsonExporter с реальным API."""

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
        msgs = [_msg(id=i, text=f"msg{i}") for i in range(1, 4)]
        data = self._run(msgs)
        ids = [m["id"] for m in data["messages"]]
        assert ids == [1, 2, 3]

    def test_topic_title_appears_in_json_header(self):
        """Если передан topic_title — он попадает в JSON."""
        data = self._run([_msg(id=1)], topic_title="General")
        assert data["topic"] == "General"

    def test_author_name_in_json(self):
        """Имя автора сохраняется в поле from."""
        data = self._run([_msg(id=1, from_name="Serge", from_username="serge")])
        assert data["messages"][0]["from"] == "Serge"
        assert data["messages"][0]["from_username"] == "serge"

    def test_close_writes_valid_json_on_cancellation(self):
        """close() дописывает закрывающие скобки — JSON остаётся валидным."""
        exp = JsonExporter()
        exp.open(self.tmpdir, "Chat")
        exp.write(_msg(id=1))
        exp.close()
        # После close файл должен существовать и быть валидным JSON
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
        # close() всё равно должен отработать без ошибок
        assert exp._file is None


class TestMarkdownExporter:
    """Тесты MarkdownExporter с реальным API."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.tmpdir = str(tmp_path)

    def _run(self, messages, settings=None, popular_min=0, chat_name="Test Chat") -> list[str]:
        exp = MarkdownExporter(settings=settings, popular_min_reactions=popular_min)
        exp.open(self.tmpdir, chat_name)
        for msg in messages:
            exp.write(msg)
        return exp.finalize()

    def _read(self, path: str) -> str:
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_empty_messages_returns_no_files(self):
        """Пустой список сообщений — нет файлов."""
        files = self._run([])
        assert files == []

    def test_single_message_creates_md_file_with_author_and_text(self):
        """Одно сообщение создаёт .md файл с именем автора и текстом."""
        files = self._run([_msg(text="Hello world", from_name="Alice")])
        assert len(files) == 1
        content = self._read(files[0])
        assert "Alice" in content
        assert "Hello world" in content

    def test_filename_contains_chat_name(self):
        """Имя файла содержит имя чата."""
        files = self._run([_msg(text="x")], chat_name="My Chat")
        basename = os.path.basename(files[0])
        assert "My_Chat" in basename

    def test_file_extension_is_md(self):
        """Файл экспорта имеет расширение .md."""
        files = self._run([_msg(text="test")])
        assert files[0].endswith(".md")

    def test_service_messages_are_skipped(self):
        """Сервисные сообщения не попадают в вывод."""
        msgs = [
            ExportMessage(id=1, type="service", date="2024-01-01T00:00:00", text="User joined"),
            _msg(id=2, text="Actual content"),
        ]
        files = self._run(msgs)
        content = self._read(files[0])
        assert "User joined" not in content
        assert "Actual content" in content

    def test_message_with_timestamp(self):
        """Временная метка появляется в выводе."""
        settings = MarkdownSettings(include_timestamps=True, include_author=False,
                                     date_format="YYYY-MM-DD")
        files = self._run([_msg(date="2024-06-15T10:00:00+00:00", text="Hi")], settings=settings)
        content = self._read(files[0])
        assert "2024-06-15" in content

    def test_plain_text_strips_markdown(self):
        """В plain_text режиме markdown-разметка удаляется."""
        settings = MarkdownSettings(plain_text=True, include_timestamps=False, include_author=False)
        files = self._run([_msg(text="**Bold** and `code`")], settings=settings)
        content = self._read(files[0])
        assert "**" not in content
        assert "Bold" in content
