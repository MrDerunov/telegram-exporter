"""Сквозной сценарий: авторизация → экспорт через CLI-команды."""

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


class TestExportEndToEnd(TestCliCommandBase):
    """Сквозные тесты: CLI-команды auth → export."""

    def test_full_flow_auth_and_export(self, tmp_path: Path):
        """Полный цикл: проверка авторизации → экспорт через CLI-команды."""
        chat_id = -1001234567890

        user = make_fake_user(id=1, username="sender")
        chat = make_fake_chat(id=chat_id, title="Test Chat", broadcast=True)
        dialog = make_fake_dialog(dialog_id=chat_id, name="Test Chat", entity=chat, is_channel=True)

        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(chat_id, [
            make_fake_message(msg_id=i, text=f"Msg {i}", sender=user)
            for i in range(1, 101)
        ])

        # Шаг 1: проверка авторизации
        result = self._invoke("auth", "status")
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        # Шаг 2: экспорт
        output_dir = tmp_path / "export" / "test_chat"
        result = self._invoke(
            "export", "--chat", str(chat_id),
            "--output", str(output_dir),
            "--format", "json",
            "--last", "20",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        # Проверка результата
        export_dirs = list(output_dir.glob("Test_Chat_*"))
        assert len(export_dirs) == 1, f"Expected 1 export dir, got {len(export_dirs)}"

        result_file = export_dirs[0] / "result.json"
        assert result_file.exists(), f"result.json not found in {export_dirs[0]}"

        data = json.loads(result_file.read_text(encoding="utf-8"))
        assert "messages" in data
        assert len(data["messages"]) > 0
        assert len(data["messages"]) <= 20
