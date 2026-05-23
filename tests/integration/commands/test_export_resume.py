"""Интеграционные тесты CLI-команды export: --resume."""

from __future__ import annotations

import json
import time
from pathlib import Path

from tests.common.fakes.factories import (
    make_fake_user,
    make_fake_chat,
    make_fake_dialog,
    make_fake_message,
)
from tests.integration.commands.test_cli_command_base import TestCliCommandBase
from datetime import UTC


class TestExportResume(TestCliCommandBase):
    """Тесты атрибута --resume (продолжение прерванного экспорта)."""

    def _setup_chat_with_messages(self, num_messages: int = 50):
        user = make_fake_user(id=1, username="u")
        chat = make_fake_chat(id=-1001234, title="Resume Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Resume Chat", entity=chat)
        from datetime import datetime, timedelta
        now = datetime.now(UTC)
        msgs = []
        for i in range(1, num_messages + 1):
            # В Telegram ID растут со временем: старые → малый ID, новые → большой ID
            age_hours = num_messages - i + 1
            msgs.append(make_fake_message(
                msg_id=i,
                text=f"Msg {i}",
                date=now - timedelta(hours=age_hours),
            ))
        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(-1001234, msgs)
        return user, chat, dialog, msgs

    def test_resume_without_history_starts_fresh(self, tmp_path: Path):
        """--resume без предыдущей истории запускает полный экспорт."""
        self._setup_chat_with_messages(10)

        result = self._invoke(
            "export", "run", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "json", "--resume",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("Resume_Chat_*"))
        data = json.loads((export_dirs[0] / "result.json").read_text(encoding="utf-8"))
        assert len(data["messages"]) == 10

    def test_resume_skips_already_exported(self, tmp_path: Path):
        """--resume пропускает сообщения, экспортированные ранее."""
        self._setup_chat_with_messages(30)

        output = tmp_path / "resume_test"
        output.mkdir(parents=True, exist_ok=True)

        # Первый экспорт 5 сообщений (без --resume)
        result1 = self._invoke(
            "export", "run", "--chat", "-1001234", "--output", str(output),
            "--format", "json", "--last", "5",
        )
        assert result1.exit_code == 0, f"STDERR: {result1.stderr}"

        export_dirs1 = sorted(output.glob("Resume_Chat_*"))
        assert len(export_dirs1) == 1
        data1 = json.loads((export_dirs1[0] / "result.json").read_text(encoding="utf-8"))
        assert len(data1["messages"]) == 5
        first_export_ids = {m["id"] for m in data1["messages"]}

        # Копируем export_history.json в output_dir для --resume
        import shutil
        shutil.copy(
            export_dirs1[0] / "export_history.json",
            output / "export_history.json",
        )

        # Пауза для гарантии разных timestamp в именах директорий
        time.sleep(1.1)

        # Второй экспорт: с --resume из той же директории, --last 10
        result2 = self._invoke(
            "export", "run", "--chat", "-1001234", "--output", str(output),
            "--format", "json", "--last", "10", "--resume",
        )
        assert result2.exit_code == 0, f"STDERR: {result2.stderr}"

        export_dirs2 = sorted(output.glob("Resume_Chat_*"))
        assert len(export_dirs2) >= 2, (
            f"Expected at least 2 dirs, got {len(export_dirs2)}"
        )
        data2 = json.loads((export_dirs2[1] / "result.json").read_text(encoding="utf-8"))
        second_export_ids = {m["id"] for m in data2["messages"]}
        # ID из первого экспорта не должны повторяться
        assert first_export_ids.isdisjoint(second_export_ids), (
            f"Overlap: {first_export_ids & second_export_ids}"
        )
