"""Интеграционные тесты CLI-команды export: --chat, --output, --format."""

from __future__ import annotations

import json
from pathlib import Path

from tests.common.fakes.factories import (
    make_fake_user,
    make_fake_chat,
    make_fake_dialog,
    make_fake_message,
)
from tests.integration.commands.test_cli_command_base import TestCliCommandBase
from datetime import UTC


class TestExportBasic(TestCliCommandBase):
    """Тесты базовых атрибутов: --chat, --output, --format."""

    def test_fail_when_chat_is_missing(self):
        """export run без --chat должен упасть с ошибкой."""
        result = self._invoke("export", "run")
        assert result.exit_code != 0

    def test_export_with_chat_and_output_creates_directory(self, tmp_path: Path):
        """export run --chat --output создаёт директорию с файлами."""
        user = make_fake_user(id=1, username="test_user")
        chat = make_fake_chat(id=-1001234, title="Test Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Test Chat", entity=chat)
        msgs = [make_fake_message(msg_id=i, text=f"Msg {i}") for i in range(5, 0, -1)]

        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(-1001234, msgs)

        result = self._invoke(
            "export", "run", "--chat", "-1001234", "--output", str(tmp_path),
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        # Проверяем что создалась директория экспорта
        export_dirs = list(tmp_path.glob("Test_Chat_*"))
        assert len(export_dirs) == 1, f"Expected 1 export dir, got {export_dirs}"
        export_dir = export_dirs[0]
        assert export_dir.is_dir()

        # По умолчанию --format both: должны быть result.json и .md
        json_file = export_dir / "result.json"
        md_files = list(export_dir.glob("*.md"))
        assert json_file.exists(), f"result.json not found in {export_dir}"
        assert len(md_files) > 0, f"No .md files in {export_dir}"

    def test_export_format_json_creates_only_json(self, tmp_path: Path):
        """export run --format json создаёт только result.json."""
        user = make_fake_user(id=1, username="test_user")
        chat = make_fake_chat(id=-1001234, title="JSON Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="JSON Chat", entity=chat)
        msgs = [make_fake_message(msg_id=1, text="Hello JSON")]

        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(-1001234, msgs)

        result = self._invoke(
            "export", "run", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "json",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("JSON_Chat_*"))
        assert len(export_dirs) == 1
        json_file = export_dirs[0] / "result.json"
        assert json_file.exists()

        data = json.loads(json_file.read_text(encoding="utf-8"))
        assert "messages" in data
        assert len(data["messages"]) == 1
        assert data["messages"][0]["text"] == "Hello JSON"

    def test_export_format_markdown_creates_only_md(self, tmp_path: Path):
        """export run --format markdown создаёт только .md файлы."""
        user = make_fake_user(id=1, username="test_user")
        chat = make_fake_chat(id=-1001234, title="MD Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="MD Chat", entity=chat)
        msgs = [make_fake_message(msg_id=1, text="Hello Markdown")]

        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(-1001234, msgs)

        result = self._invoke(
            "export", "run", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "markdown",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("MD_Chat_*"))
        assert len(export_dirs) == 1
        json_file = export_dirs[0] / "result.json"
        assert not json_file.exists()

        md_files = list(export_dirs[0].glob("*.md"))
        assert len(md_files) > 0

    def test_export_format_both_creates_both(self, tmp_path: Path):
        """export run --format both создаёт и result.json и .md."""
        user = make_fake_user(id=1, username="test_user")
        chat = make_fake_chat(id=-1001234, title="Both Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Both Chat", entity=chat)
        msgs = [make_fake_message(msg_id=1, text="Both formats")]

        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(-1001234, msgs)

        result = self._invoke(
            "export", "run", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "both",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("Both_Chat_*"))
        assert len(export_dirs) == 1
        assert (export_dirs[0] / "result.json").exists()
        assert len(list(export_dirs[0].glob("*.md"))) > 0

    def test_export_with_username_chat(self, tmp_path: Path):
        """export run с username вместо числового ID."""
        user = make_fake_user(id=1, username="test_user")
        chat = make_fake_chat(id=-1005678, title="Username Chat")
        # username-based search: entity.username должен совпадать
        chat.username = "test_channel"
        dialog = make_fake_dialog(dialog_id=-1005678, name="Username Chat", entity=chat)
        msgs = [make_fake_message(msg_id=1, text="Via username")]

        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(-1005678, msgs)

        result = self._invoke(
            "export", "run", "--chat", "test_channel", "--output", str(tmp_path),
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("Username_Chat_*"))
        assert len(export_dirs) == 1

    def test_export_chat_not_found(self, tmp_path: Path):
        """export run с несуществующим чатом падает с ошибкой."""
        result = self._invoke(
            "export", "run", "--chat", "-9999999", "--output", str(tmp_path),
        )
        assert result.exit_code != 0

    def test_export_with_default_output_dir(self, tmp_path: Path):
        """export run без --output использует директорию по умолчанию."""
        import os
        user = make_fake_user(id=1, username="test_user")
        chat = make_fake_chat(id=-1001234, title="Default Dir")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Default Dir", entity=chat)
        msgs = [make_fake_message(msg_id=1, text="Default output")]

        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(-1001234, msgs)

        # Меняем CWD на tmp_path чтобы export/ создалась там
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = self._invoke("export", "run", "--chat", "-1001234")
            assert result.exit_code == 0, f"STDERR: {result.stderr}"

            export_root = tmp_path / "export" / "-1001234"
            assert export_root.exists()
        finally:
            os.chdir(old_cwd)

    def test_export_json_contains_correct_fields(self, tmp_path: Path):
        """result.json содержит корректные поля сообщений."""
        from datetime import datetime, timezone

        user = make_fake_user(id=1, username="sender")
        chat = make_fake_chat(id=-1001234, title="Fields Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Fields Chat", entity=chat)
        msg = make_fake_message(
            msg_id=42,
            text="Field test",
            date=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
            sender=user,
            views=100,
            forwards=5,
        )

        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(-1001234, [msg])

        result = self._invoke(
            "export", "run", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "json",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("Fields_Chat_*"))
        json_file = export_dirs[0] / "result.json"
        data = json.loads(json_file.read_text(encoding="utf-8"))
        m = data["messages"][0]
        assert m["id"] == 42
        assert m["text"] == "Field test"
        assert m["type"] == "message"
        assert "date" in m

    def test_export_without_messages_still_creates_valid_output(self, tmp_path: Path):
        """Экспорт чата без сообщений создаёт валидный вывод."""
        user = make_fake_user(id=1, username="test_user")
        chat = make_fake_chat(id=-1001234, title="Empty Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Empty Chat", entity=chat)

        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        # Нет сообщений

        result = self._invoke(
            "export", "run", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "json",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("Empty_Chat_*"))
        assert len(export_dirs) == 1
        json_file = export_dirs[0] / "result.json"
        data = json.loads(json_file.read_text(encoding="utf-8"))
        assert data["messages"] == []
