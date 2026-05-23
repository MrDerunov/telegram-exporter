"""Интеграционные тесты CLI-команды export: --topic-id."""

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


class TestExportTopic(TestCliCommandBase):
    """Тесты атрибута --topic-id."""

    def test_topic_id_filters_messages(self, tmp_path: Path):
        """--topic-id экспортирует только сообщения указанного топика."""
        user = make_fake_user(id=1, username="u")
        chat = make_fake_chat(id=-1001234, title="Forum Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Forum Chat", entity=chat)
        msgs = [
            make_fake_message(msg_id=1, text="Topic 5 msg",
                              reply_to_msg_id=5),
            make_fake_message(msg_id=2, text="Topic 5 msg 2",
                              reply_to_msg_id=5),
            make_fake_message(msg_id=3, text="Main thread"),
            make_fake_message(msg_id=4, text="Topic 10 msg",
                              reply_to_msg_id=10),
        ]
        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(-1001234, msgs)

        result = self._invoke(
            "export", "run", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "json", "--topic-id", "5",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("Forum_Chat_*"))
        data = json.loads((export_dirs[0] / "result.json").read_text(encoding="utf-8"))
        msg_ids = [m["id"] for m in data["messages"]]
        assert 1 in msg_ids
        assert 2 in msg_ids
        assert 3 not in msg_ids  # main thread
        assert 4 not in msg_ids  # topic 10
