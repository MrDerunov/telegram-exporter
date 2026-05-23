"""Интеграционные тесты CLI-команды export: --deduplicate."""

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
from datetime import UTC, datetime


class TestExportDeduplicate(TestCliCommandBase):
    """Тесты атрибута --deduplicate (пропуск уже экспортированных сообщений)."""

    def _setup_chat_with_messages(self, num_messages: int = 50):
        user = make_fake_user(id=1, username="u")
        chat = make_fake_chat(id=-1001234, title="Dedup Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Dedup Chat", entity=chat)
        from datetime import timedelta
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

    def test_deduplicate_skips_previously_exported(self, tmp_path: Path):
        """--deduplicate пропускает сообщения из предыдущего экспорта."""
        self._setup_chat_with_messages(30)

        output = tmp_path / "dedup_test"
        output.mkdir(parents=True, exist_ok=True)

        # Первый экспорт 5 сообщений (без --deduplicate)
        result1 = self._invoke(
            "export", "--chat", "-1001234", "--output", str(output),
            "--format", "json", "--last", "5",
        )
        assert result1.exit_code == 0, f"STDERR: {result1.stderr}"

        export_dirs1 = sorted(output.glob("Dedup_Chat_*"))
        assert len(export_dirs1) == 1
        data1 = json.loads((export_dirs1[0] / "result.json").read_text(encoding="utf-8"))
        first_ids = {m["id"] for m in data1["messages"]}
        assert len(first_ids) == 5

        # Пауза чтобы гарантировать разные timestamp в именах директорий
        time.sleep(1.1)

        # Второй экспорт: с --deduplicate, --last 10
        result2 = self._invoke(
            "export", "--chat", "-1001234", "--output", str(output),
            "--format", "json", "--last", "10", "--deduplicate",
        )
        assert result2.exit_code == 0, f"STDERR: {result2.stderr}"

        export_dirs2 = sorted(output.glob("Dedup_Chat_*"))
        assert len(export_dirs2) >= 2, (
            f"Expected at least 2 dirs, got {len(export_dirs2)}"
        )
        data2 = json.loads((export_dirs2[1] / "result.json").read_text(encoding="utf-8"))
        second_ids = {m["id"] for m in data2["messages"]}
        # ID из первого экспорта не должны повторяться
        assert first_ids.isdisjoint(second_ids), (
            f"Overlap: {first_ids & second_ids}"
        )

    def test_deduplicate_without_history_exports_all(self, tmp_path: Path):
        """--deduplicate без предыдущей истории экспортирует все сообщения."""
        self._setup_chat_with_messages(10)

        result = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "json", "--deduplicate",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("Dedup_Chat_*"))
        data = json.loads((export_dirs[0] / "result.json").read_text(encoding="utf-8"))
        assert len(data["messages"]) == 10

    def test_deduplicate_creates_fresh_export_directory(self, tmp_path: Path):
        """--deduplicate создаёт новую директорию (не перезаписывает старую)."""
        self._setup_chat_with_messages(10)

        # Первый экспорт
        result1 = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "json", "--last", "3",
        )
        assert result1.exit_code == 0, f"STDERR: {result1.stderr}"

        export_dirs1 = sorted(tmp_path.glob("Dedup_Chat_*"))
        assert len(export_dirs1) == 1

        # Пауза для гарантии разных имён директорий
        time.sleep(1.1)

        # Второй экспорт с --deduplicate
        result2 = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "json", "--last", "7", "--deduplicate",
        )
        assert result2.exit_code == 0, f"STDERR: {result2.stderr}"

        # Должно быть две разные директории
        export_dirs = sorted(tmp_path.glob("Dedup_Chat_*"))
        assert len(export_dirs) >= 2, (
            f"Expected at least 2 dirs, got {len(export_dirs)}"
        )

    def test_deduplicate_with_topic_id(self, tmp_path: Path):
        """--deduplicate с --topic-id корректно работает вместе."""
        user = make_fake_user(id=1, username="u")
        chat = make_fake_chat(id=-1001234, title="Forum Dedup")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Forum Dedup", entity=chat)
        msgs = [
            make_fake_message(msg_id=5, text="T1 msg1", reply_to_msg_id=5),
            make_fake_message(msg_id=4, text="T1 msg2", reply_to_msg_id=5),
            make_fake_message(msg_id=3, text="Main msg"),
            make_fake_message(msg_id=2, text="T2 msg", reply_to_msg_id=10),
        ]
        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(-1001234, msgs)

        result = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "json", "--topic-id", "5", "--deduplicate",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("Forum_Dedup_*"))
        data = json.loads((export_dirs[0] / "result.json").read_text(encoding="utf-8"))
        msg_ids = {m["id"] for m in data["messages"]}
        assert 5 in msg_ids
        assert 4 in msg_ids
        assert 3 not in msg_ids  # main thread
        assert 2 not in msg_ids  # different topic
