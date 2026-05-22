"""
Тесты MarkdownExporter — объединённые из Phase 1 (unittest) и Phase 2 (pytest).
"""
from __future__ import annotations

import os
import pytest

from tg_exporter.services.export.models.export_message import ExportMessage
from tg_exporter.services.export.models.reaction_item import ReactionItem
from tg_exporter.services.export.models.poll_data import PollData, PollAnswer
from tg_exporter.settings.configs.markdown_config import MarkdownConfig
from tg_exporter.services.export.exporters.markdown_exporter import MarkdownExporter, _format_message


def _msg(**kw) -> ExportMessage:
    defaults = dict(id=1, type="message", date="2024-06-15T10:00:00+00:00", text="Hello")
    defaults.update(kw)
    return ExportMessage(**defaults)


class TestMarkdownExporter:
    """Интеграционные тесты MarkdownExporter."""

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

    def test_return_no_files_when_empty(self):
        """Пустой список сообщений — нет файлов."""
        files = self._run([])
        assert files == []

    def test_create_file_with_author_and_text_for_single_message(self):
        """Одно сообщение создаёт .md файл с именем автора и текстом."""
        files = self._run([_msg(text="Hello world", from_name="Alice")])
        assert len(files) == 1
        content = self._read(files[0])
        assert "Alice" in content
        assert "Hello world" in content

    def test_contain_chat_name_in_filename(self):
        """Имя файла содержит имя чата."""
        files = self._run([_msg(text="x")], chat_name="My Chat")
        basename = os.path.basename(files[0])
        assert "My_Chat" in basename

    def test_have_md_extension(self):
        """Файл экспорта имеет расширение .md."""
        files = self._run([_msg(text="test")])
        assert files[0].endswith(".md")

    def test_skip_service_messages(self):
        """Сервисные сообщения не попадают в вывод."""
        msgs = [
            ExportMessage(id=1, type="service", date="2024-01-01T00:00:00", text="User joined"),
            _msg(id=2, text="Actual content"),
        ]
        files = self._run(msgs)
        content = self._read(files[0])
        assert "User joined" not in content
        assert "Actual content" in content

    def test_include_timestamp(self):
        """Временная метка появляется в выводе."""
        settings = MarkdownConfig(include_timestamps=True, include_author=False,
                                  date_format="YYYY-MM-DD")
        files = self._run([_msg(date="2024-06-15T10:00:00+00:00", text="Hi")], settings=settings)
        content = self._read(files[0])
        assert "2024-06-15" in content

    def test_strip_markdown_in_plain_text_mode(self):
        """В plain_text режиме markdown-разметка удаляется."""
        settings = MarkdownConfig(plain_text=True, include_timestamps=False, include_author=False)
        files = self._run([_msg(text="**Bold** and `code`")], settings=settings)
        content = self._read(files[0])
        assert "**" not in content
        assert "Bold" in content

    def test_not_have_utf8_bom(self):
        """В начале .md файла нет BOM."""
        files = self._run([_msg(text="test")])
        with open(files[0], "rb") as f:
            raw = f.read(3)
        assert raw != b"\xef\xbb\xbf"

    def test_create_multiple_files_when_exceeding_word_limit(self):
        """При превышении лимита слов создаются несколько файлов."""
        settings = MarkdownConfig(words_per_file=5, include_timestamps=False, include_author=False)
        msgs = [_msg(id=i, text="one two three four") for i in range(1, 4)]
        files = self._run(msgs, settings=settings)
        assert len(files) > 1

    def test_create_popular_file_when_reactions_exceed_threshold(self):
        """При превышении порога реакций создаётся файл популярных сообщений."""
        msg = _msg(id=1, text="Viral", reactions=(ReactionItem(emoji="🔥", count=10),))
        files = self._run([msg], popular_min=5)
        popular_files = [f for f in files if "popular" in os.path.basename(f)]
        assert len(popular_files) == 1
        content = self._read(popular_files[0])
        assert "Viral" in content

    def test_not_create_popular_file_when_below_threshold(self):
        """При реакциях ниже порога популярный файл не создаётся."""
        msg = _msg(id=1, text="Low", reactions=(ReactionItem(emoji="👍", count=2),))
        files = self._run([msg], popular_min=5)
        popular_files = [f for f in files if "popular" in os.path.basename(f)]
        assert len(popular_files) == 0

    def test_not_crash_on_finalize_with_only_service_messages(self):
        """finalize() не падает если весь контент — сервисные сообщения."""
        exp = MarkdownExporter()
        exp.open(self.tmpdir, "Empty")
        exp.write(ExportMessage(id=1, type="service", date="2024-01-01T00:00:00", text=""))
        files = exp.finalize()
        assert files == []


class TestFormatMessage:
    """Unit-тесты хелпера _format_message (из Phase 1)."""

    def test_return_text_only(self):
        s = MarkdownConfig(include_timestamps=False, include_author=False)
        result = _format_message(_msg(text="Hello"), s)
        assert result == "Hello"

    def test_include_author(self):
        s = MarkdownConfig(include_timestamps=False, include_author=True)
        result = _format_message(_msg(text="Hi", from_name="Alice"), s)
        assert "Alice" in result
        assert "Hi" in result

    def test_strip_markdown_in_plain_text(self):
        s = MarkdownConfig(plain_text=True, include_timestamps=False, include_author=False)
        result = _format_message(_msg(text="**Bold** and `code`"), s)
        assert "**" not in result
        assert "`" not in result
        assert "Bold" in result

    def test_format_timestamp(self):
        s = MarkdownConfig(include_timestamps=True, include_author=False, date_format="YYYY-MM-DD")
        result = _format_message(_msg(date="2024-06-15T10:00:00+00:00", text="Hi"), s)
        assert "2024-06-15" in result

    def test_format_reactions(self):
        s = MarkdownConfig(include_reactions=True, include_timestamps=False, include_author=False)
        msg = _msg(text="Hi", reactions=(ReactionItem(emoji="👍", count=5),))
        result = _format_message(msg, s)
        assert "👍" in result
        assert "5" in result

    def test_format_poll(self):
        s = MarkdownConfig(include_polls=True, include_timestamps=False, include_author=False)
        poll = PollData(
            question="Что выбрать?",
            answers=(PollAnswer(text="A", voters=2), PollAnswer(text="B", voters=3)),
            total_voters=5,
        )
        result = _format_message(_msg(text="", poll=poll), s)
        assert "Что выбрать?" in result
        assert "5" in result

    def test_format_forwarded_from(self):
        s = MarkdownConfig(include_forwarded=True, include_timestamps=False, include_author=False)
        msg = _msg(text="Hi", forwarded_from="Bob")
        result = _format_message(msg, s)
        assert "Bob" in result

    def test_format_transcription(self):
        s = MarkdownConfig(include_timestamps=False, include_author=False)
        msg = _msg(text="", transcription="Привет мир")
        result = _format_message(msg, s)
        assert "Транскрипция" in result
        assert "Привет мир" in result
