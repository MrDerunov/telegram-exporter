"""Интеграционные тесты CLI-команды export: --words-per-file."""

from __future__ import annotations

from pathlib import Path

from tests.common.fakes.factories import (
    make_fake_user,
    make_fake_chat,
    make_fake_dialog,
    make_fake_message,
)
from tests.integration.commands.test_cli_command_base import TestCliCommandBase


class TestExportWordsPerFile(TestCliCommandBase):
    """Тесты атрибута --words-per-file."""

    def _setup_chat_with_messages(self, num_messages: int = 10, text: str = "word "):
        user = make_fake_user(id=1, username="u")
        chat = make_fake_chat(id=-1001234, title="Words Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Words Chat", entity=chat)
        msgs = [
            make_fake_message(msg_id=i, text=f"{text * 5} msg{i}")
            for i in range(num_messages, 0, -1)
        ]
        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(-1001234, msgs)

    def test_words_per_file_custom_creates_chunked_output(self, tmp_path: Path):
        """--words-per-file с указанным значением создаёт .md файлы с разбивкой."""
        self._setup_chat_with_messages(
            num_messages=30,
            text="word " * 30,
        )

        result = self._invoke(
            "export", "run", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "markdown", "--words-per-file", "200",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("Words_Chat_*"))
        md_files = list(export_dirs[0].glob("*.md"))
        # Хотя бы один _part_N.md файл должен быть создан
        part_files = [f for f in md_files if "_part_" in f.name]
        assert len(part_files) >= 1, (
            f"Expected at least 1 _part_N.md file, got {len(part_files)}"
        )

    def test_words_per_file_default_creates_one_file(self, tmp_path: Path):
        """С дефолтным --words-per-file (50000) мало сообщений → 1 файл."""
        self._setup_chat_with_messages(num_messages=5, text="short ")

        result = self._invoke(
            "export", "run", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "markdown",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("Words_Chat_*"))
        md_files = list(export_dirs[0].glob("*.md"))
        # Только один файл (мало слов)
        part_files = [f for f in md_files if "_part_" in f.name]
        assert len(part_files) <= 1, (
            f"Expected at most 1 part, got {len(part_files)}"
        )
