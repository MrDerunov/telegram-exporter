"""Интеграционные тесты CLI-команды export: --all, --skip-unavailable."""

from __future__ import annotations

from pathlib import Path

from tests.common.fakes.factories import (
    make_fake_user,
    make_fake_chat,
    make_fake_dialog,
    make_fake_message,
)
from tests.integration.commands.test_cli_command_base import TestCliCommandBase


class TestExportAll(TestCliCommandBase):
    """Тесты атрибутов --all и --skip-unavailable."""

    def _setup_state_with_chats(self):
        """Добавить чаты в StateModel."""
        from tg_exporter.settings.configs import StateModel, ChatEntry

        state = StateModel(
            chats=(
                ChatEntry(id=-1001234, name="Chat A"),
                ChatEntry(id=-1005678, name="Chat B"),
            )
        )
        self.host._container.register_instance(StateModel, state)

    def _setup_dialogs_and_messages(self):
        """Создать диалоги и сообщения для обоих чатов."""
        user = make_fake_user(id=1, username="u")
        chat_a = make_fake_chat(id=-1001234, title="Chat A")
        chat_b = make_fake_chat(id=-1005678, title="Chat B")
        dialog_a = make_fake_dialog(dialog_id=-1001234, name="Chat A", entity=chat_a)
        dialog_b = make_fake_dialog(dialog_id=-1005678, name="Chat B", entity=chat_b)

        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog_a)
        self.server.dialogs.add_dialog(dialog_b)
        self.server.messages.add_messages(-1001234, [
            make_fake_message(msg_id=2, text="A2"),
            make_fake_message(msg_id=1, text="A1"),
        ])
        self.server.messages.add_messages(-1005678, [
            make_fake_message(msg_id=1, text="B1"),
        ])

    def test_export_all_exports_all_chats(self, tmp_path: Path):
        """--all экспортирует все чаты из конфига."""
        self._setup_state_with_chats()
        self._setup_dialogs_and_messages()

        result = self._invoke(
            "export", "--all", "--output", str(tmp_path),
            "--format", "json",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        # Должны быть созданы директории для обоих чатов
        dirs_a = list(tmp_path.glob("Chat_A_*"))
        dirs_b = list(tmp_path.glob("Chat_B_*"))
        assert len(dirs_a) == 1, f"No export dir for Chat A in {tmp_path}"
        assert len(dirs_b) == 1, f"No export dir for Chat B in {tmp_path}"

    def test_export_all_empty_config_shows_error(self, tmp_path: Path):
        """--all без чатов в конфиге показывает ошибку."""
        from tg_exporter.settings.configs import StateModel
        state = StateModel(chats=())
        self.host._container.register_instance(StateModel, state)

        result = self._invoke(
            "export", "--all", "--output", str(tmp_path),
        )
        assert result.exit_code != 0

    def test_export_all_skip_unavailable_continues_on_error(self, tmp_path: Path):
        """--skip-unavailable пропускает чаты, которые не найдены."""
        from tg_exporter.settings.configs import StateModel, ChatEntry

        state = StateModel(
            chats=(
                ChatEntry(id=-1001234, name="Chat A"),
                ChatEntry(id=-9999999, name="Missing Chat"),
                ChatEntry(id=-1005678, name="Chat B"),
            )
        )
        self.host._container.register_instance(StateModel, state)

        user = make_fake_user(id=1, username="u")
        chat_a = make_fake_chat(id=-1001234, title="Chat A")
        chat_b = make_fake_chat(id=-1005678, title="Chat B")
        dialog_a = make_fake_dialog(dialog_id=-1001234, name="Chat A", entity=chat_a)
        dialog_b = make_fake_dialog(dialog_id=-1005678, name="Chat B", entity=chat_b)

        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog_a)
        self.server.dialogs.add_dialog(dialog_b)
        self.server.messages.add_messages(-1001234, [
            make_fake_message(msg_id=1, text="A1"),
        ])
        self.server.messages.add_messages(-1005678, [
            make_fake_message(msg_id=1, text="B1"),
        ])

        result = self._invoke(
            "export", "--all", "--output", str(tmp_path),
            "--format", "json", "--skip-unavailable",
        )
        # Должен успешно завершиться, пропустив Missing Chat
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        dirs_a = list(tmp_path.glob("Chat_A_*"))
        dirs_b = list(tmp_path.glob("Chat_B_*"))
        assert len(dirs_a) == 1, "Chat A was not exported"
        assert len(dirs_b) == 1, "Chat B was not exported"

    def test_export_all_fails_on_missing_chat(self, tmp_path: Path):
        """--all без --skip-unavailable падает при недоступном чате."""
        from tg_exporter.settings.configs import StateModel, ChatEntry

        state = StateModel(
            chats=(
                ChatEntry(id=-1001234, name="Chat A"),
                ChatEntry(id=-9999999, name="Missing Chat"),
            )
        )
        self.host._container.register_instance(StateModel, state)

        user = make_fake_user(id=1, username="u")
        chat_a = make_fake_chat(id=-1001234, title="Chat A")
        dialog_a = make_fake_dialog(dialog_id=-1001234, name="Chat A", entity=chat_a)

        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog_a)
        self.server.messages.add_messages(-1001234, [
            make_fake_message(msg_id=1, text="A1"),
        ])

        result = self._invoke(
            "export", "--all", "--output", str(tmp_path),
            "--format", "json",
        )
        # Должен упасть, так как --skip-unavailable не указан
        assert result.exit_code != 0
