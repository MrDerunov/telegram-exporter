"""Интеграционные тесты CLI-команд chats: list, show, add, remove."""

from __future__ import annotations

from pathlib import Path

from tests.common.fakes.factories import (
    make_fake_user,
    make_fake_chat,
    make_fake_dialog,
)
from tests.integration.commands.test_cli_command_base import TestCliCommandBase


# ---------------------------------------------------------------------------
# chats list
# ---------------------------------------------------------------------------


class TestChatsList(TestCliCommandBase):
    """Тесты команды chats list."""

    def test_list_all_chats(self):
        """chats list показывает все диалоги."""
        user = make_fake_user(id=1)
        chat = make_fake_chat(id=-1001234, title="Test Channel")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Test Channel", entity=chat, is_channel=True)
        dialog2 = make_fake_dialog(dialog_id=12345, name="Test User", is_user=True)

        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.dialogs.add_dialog(dialog2)

        result = self._invoke("chats", "list")
        assert result.exit_code == 0, f"STDERR: {result.stderr}"
        assert "Test Channel" in result.output
        assert "Test User" in result.output

    def test_list_empty(self):
        """chats list без диалогов."""
        result = self._invoke("chats", "list")
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

    def test_list_with_search_found(self):
        """chats list --search фильтрует по названию."""
        d1 = make_fake_dialog(dialog_id=1, name="Work Chat")
        d2 = make_fake_dialog(dialog_id=2, name="Personal Stuff")
        d3 = make_fake_dialog(dialog_id=3, name="Another Work Group")

        self.server.dialogs.add_dialog(d1)
        self.server.dialogs.add_dialog(d2)
        self.server.dialogs.add_dialog(d3)

        result = self._invoke("chats", "list", "--search", "Work")
        assert result.exit_code == 0, f"STDERR: {result.stderr}"
        assert "Work Chat" in result.output
        assert "Another Work Group" in result.output
        assert "Personal Stuff" not in result.output

    def test_list_with_search_not_found(self):
        """chats list --search без совпадений."""
        d1 = make_fake_dialog(dialog_id=1, name="Only Chat")
        self.server.dialogs.add_dialog(d1)

        result = self._invoke("chats", "list", "--search", "nothing")
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

    def test_list_with_folder(self):
        """chats list --folder фильтрует по папке."""
        d1 = make_fake_dialog(dialog_id=1, name="Work A", folder="Work")
        d2 = make_fake_dialog(dialog_id=2, name="Personal", folder="Personal")
        d3 = make_fake_dialog(dialog_id=3, name="Work B", folder="Work")

        self.server.dialogs.add_dialog(d1)
        self.server.dialogs.add_dialog(d2)
        self.server.dialogs.add_dialog(d3)

        result = self._invoke("chats", "list", "--folder", "Work")
        assert result.exit_code == 0, f"STDERR: {result.stderr}"
        assert "Work A" in result.output
        assert "Work B" in result.output
        assert "Personal" not in result.output

    def test_list_folders_only(self):
        """chats list --folders показывает только названия папок."""
        d1 = make_fake_dialog(dialog_id=1, name="Chat 1", folder="Important")
        d2 = make_fake_dialog(dialog_id=2, name="Chat 2", folder="Archive")
        d3 = make_fake_dialog(dialog_id=3, name="Chat 3", folder="Important")

        self.server.dialogs.add_dialog(d1)
        self.server.dialogs.add_dialog(d2)
        self.server.dialogs.add_dialog(d3)

        result = self._invoke("chats", "list", "--folders")
        assert result.exit_code == 0, f"STDERR: {result.stderr}"
        assert "Important" in result.output
        assert "Archive" in result.output
        assert "Chat 1" not in result.output

    def test_list_folders_only_empty(self):
        """chats list --folders без папок."""
        d1 = make_fake_dialog(dialog_id=1, name="Chat")
        self.server.dialogs.add_dialog(d1)

        result = self._invoke("chats", "list", "--folders")
        assert result.exit_code == 0, f"STDERR: {result.stderr}"


# ---------------------------------------------------------------------------
# chats show
# ---------------------------------------------------------------------------


class TestChatsShow(TestCliCommandBase):
    """Тесты команды chats show."""

    def test_show_existing_chat(self):
        """chats show --chat показывает информацию о чате."""
        chat = make_fake_chat(id=-1001234, title="My Channel")
        dialog = make_fake_dialog(dialog_id=-1001234, name="My Channel", entity=chat, is_channel=True)
        self.server.dialogs.add_dialog(dialog)

        result = self._invoke("chats", "show", "--chat", "-1001234")
        assert result.exit_code == 0, f"STDERR: {result.stderr}"
        assert "My Channel" in result.output
        assert "-1001234" in result.output

    def test_show_chat_not_found(self):
        """chats show --chat для несуществующего чата."""
        result = self._invoke("chats", "show", "--chat", "-9999999")
        assert result.exit_code != 0

    def test_show_missing_chat_arg(self):
        """chats show без --chat вызывает ошибку."""
        result = self._invoke("chats", "show")
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# chats add
# ---------------------------------------------------------------------------


class TestChatsAdd(TestCliCommandBase):
    """Тесты команды chats add."""

    def test_add_chat_by_id(self, tmp_path: Path):
        """chats add --chat добавляет чат в конфиг."""
        from tg_exporter.settings.configs import StateModel

        state = StateModel(chats=())
        self.host._container.register_instance(StateModel, state)

        chat = make_fake_chat(id=-1001234, title="New Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="New Chat", entity=chat)
        self.server.dialogs.add_dialog(dialog)

        result = self._invoke("chats", "add", "--chat", "-1001234")
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        updated = self.fake_settings.load()
        assert any(c.id == -1001234 for c in updated.chats)

    def test_add_duplicate_chat(self):
        """chats add --chat для уже существующего в конфиге чата."""
        from tg_exporter.settings.configs import StateModel, ChatEntry

        state = StateModel(chats=(ChatEntry(id=-1001234, name="Existing"),))
        self.host._container.register_instance(StateModel, state)

        chat = make_fake_chat(id=-1001234, title="Existing")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Existing", entity=chat)
        self.server.dialogs.add_dialog(dialog)

        result = self._invoke("chats", "add", "--chat", "-1001234")
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        # Чат не должен добавиться повторно
        updated = self.host.get(StateModel)
        assert len(updated.chats) == 1

    def test_add_chat_not_found(self):
        """chats add --chat для чата, которого нет в диалогах."""
        from tg_exporter.settings.configs import StateModel
        state = StateModel(chats=())
        self.host._container.register_instance(StateModel, state)

        result = self._invoke("chats", "add", "--chat", "-9999999")
        assert result.exit_code != 0

    def test_add_by_folder(self):
        """chats add --folder добавляет все чаты из папки."""
        from tg_exporter.settings.configs import StateModel

        state = StateModel(chats=())
        self.host._container.register_instance(StateModel, state)

        d1 = make_fake_dialog(dialog_id=1, name="Proj A", folder="Projects")
        d2 = make_fake_dialog(dialog_id=2, name="Proj B", folder="Projects")
        d3 = make_fake_dialog(dialog_id=3, name="Other", folder="Misc")
        self.server.dialogs.add_dialog(d1)
        self.server.dialogs.add_dialog(d2)
        self.server.dialogs.add_dialog(d3)

        result = self._invoke("chats", "add", "--folder", "Projects")
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        updated = self.fake_settings.load()
        ids = {c.id for c in updated.chats}
        assert 1 in ids
        assert 2 in ids
        assert 3 not in ids

    def test_add_folder_no_new_chats(self):
        """chats add --folder когда все чаты уже в конфиге."""
        from tg_exporter.settings.configs import StateModel, ChatEntry

        state = StateModel(chats=(ChatEntry(id=1, name="Proj A"),))
        self.host._container.register_instance(StateModel, state)

        d1 = make_fake_dialog(dialog_id=1, name="Proj A", folder="Projects")
        self.server.dialogs.add_dialog(d1)

        result = self._invoke("chats", "add", "--folder", "Projects")
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        # Ничего нового не добавлено
        updated = self.host.get(StateModel)
        assert len(updated.chats) == 1

    def test_add_missing_args(self):
        """chats add без --chat и --folder вызывает ошибку."""
        result = self._invoke("chats", "add")
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# chats remove
# ---------------------------------------------------------------------------


class TestChatsRemove(TestCliCommandBase):
    """Тесты команды chats remove."""

    def test_remove_existing_chat(self):
        """chats remove --chat удаляет чат из конфига."""
        from tg_exporter.settings.configs import StateModel, ChatEntry

        state = StateModel(chats=(
            ChatEntry(id=-1001234, name="To Delete"),
            ChatEntry(id=-1005678, name="Keep"),
        ))
        self.host._container.register_instance(StateModel, state)

        result = self._invoke("chats", "remove", "--chat", "-1001234")
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        updated = self.fake_settings.load()
        ids = {c.id for c in updated.chats}
        assert -1001234 not in ids
        assert -1005678 in ids

    def test_remove_chat_not_found(self):
        """chats remove --chat для чата, которого нет в конфиге."""
        from tg_exporter.settings.configs import StateModel, ChatEntry

        state = StateModel(chats=(ChatEntry(id=-1001234, name="Only"),))
        self.host._container.register_instance(StateModel, state)

        result = self._invoke("chats", "remove", "--chat", "-9999999")
        assert result.exit_code != 0

    def test_remove_missing_chat_arg(self):
        """chats remove без --chat вызывает ошибку."""
        result = self._invoke("chats", "remove")
        assert result.exit_code != 0
