"""Интеграционные тесты CLI-команды export: --last, --date-from, --date-to, --days."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone, UTC
from pathlib import Path

from tests.common.fakes.factories import (
    make_fake_user,
    make_fake_chat,
    make_fake_dialog,
    make_fake_message,
)
from tests.integration.commands.test_cli_command_base import TestCliCommandBase


class TestExportLast(TestCliCommandBase):
    """Тесты атрибута --last."""

    def _setup_chat_with_messages(self, num_messages: int = 100):
        user = make_fake_user(id=1, username="u")
        chat = make_fake_chat(id=-1001234, title="Last Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Last Chat", entity=chat)
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

    def test_last_limits_message_count(self, tmp_path: Path):
        """--last N экспортирует не более N сообщений."""
        self._setup_chat_with_messages(50)

        result = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "json", "--last", "5",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("Last_Chat_*"))
        data = json.loads((export_dirs[0] / "result.json").read_text(encoding="utf-8"))
        assert len(data["messages"]) == 5
        # Сообщения в хронологическом порядке (от старых к новым).
        # ID=46 = 46 часов назад (старое), ID=50 = 50 часов назад... нет,
        # в FakeTelegramClient ID растут с давностью: ID=1 = старее, ID=50 = новее.
        # --last 5 берёт 5 самых новых → ID=50,49,48,47,46 → после разворота: 46,47,48,49,50
        msg_ids = [m["id"] for m in data["messages"]]
        assert msg_ids == [46, 47, 48, 49, 50]

    def test_last_zero_exports_all(self, tmp_path: Path):
        """--last 0 = без ограничений (экспортирует все сообщения)."""
        self._setup_chat_with_messages(10)

        result = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "json", "--last", "0",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("Last_Chat_*"))
        data = json.loads((export_dirs[0] / "result.json").read_text(encoding="utf-8"))
        assert len(data["messages"]) == 10

    def test_last_conflicts_with_date_from(self, tmp_path: Path):
        """--last нельзя комбинировать с --date-from."""
        result = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--last", "10", "--date-from", "2025-01-01",
        )
        assert result.exit_code != 0

    def test_last_conflicts_with_date_to(self, tmp_path: Path):
        """--last нельзя комбинировать с --date-to."""
        result = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--last", "10", "--date-to", "2025-01-01",
        )
        assert result.exit_code != 0

    def test_last_conflicts_with_days(self, tmp_path: Path):
        """--last нельзя комбинировать с --days."""
        result = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--last", "10", "--days", "7",
        )
        assert result.exit_code != 0


class TestExportDateFrom(TestCliCommandBase):
    """Тесты атрибута --date-from."""

    def _setup_chat_with_dated_messages(self):
        user = make_fake_user(id=1, username="u")
        chat = make_fake_chat(id=-1001234, title="Date Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Date Chat", entity=chat)
        msgs = [
            make_fake_message(msg_id=1, text="Old",
                              date=datetime(2024, 6, 1, tzinfo=UTC)),
            make_fake_message(msg_id=2, text="Mid",
                              date=datetime(2025, 3, 15, tzinfo=UTC)),
            make_fake_message(msg_id=3, text="New",
                              date=datetime(2025, 12, 1, tzinfo=UTC)),
        ]
        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(-1001234, msgs)

    def test_date_from_filters_older_messages(self, tmp_path: Path):
        """--date-from отфильтровывает сообщения раньше даты."""
        self._setup_chat_with_dated_messages()

        result = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "json", "--date-from", "2025-01-01",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("Date_Chat_*"))
        data = json.loads((export_dirs[0] / "result.json").read_text(encoding="utf-8"))
        # Только Mid и New (после 2025-01-01)
        msg_ids = [m["id"] for m in data["messages"]]
        assert 2 in msg_ids
        assert 3 in msg_ids
        assert 1 not in msg_ids


class TestExportDateTo(TestCliCommandBase):
    """Тесты атрибута --date-to."""

    def _setup_chat_with_dated_messages(self):
        user = make_fake_user(id=1, username="u")
        chat = make_fake_chat(id=-1001234, title="DateTo Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="DateTo Chat", entity=chat)
        msgs = [
            make_fake_message(msg_id=1, text="Old",
                              date=datetime(2024, 6, 1, tzinfo=UTC)),
            make_fake_message(msg_id=2, text="Mid",
                              date=datetime(2025, 3, 15, tzinfo=UTC)),
            make_fake_message(msg_id=3, text="New",
                              date=datetime(2025, 12, 1, tzinfo=UTC)),
        ]
        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(-1001234, msgs)

    def test_date_to_filters_newer_messages(self, tmp_path: Path):
        """--date-to отфильтровывает сообщения позже даты."""
        self._setup_chat_with_dated_messages()

        result = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "json", "--date-to", "2025-06-01",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("DateTo_Chat_*"))
        data = json.loads((export_dirs[0] / "result.json").read_text(encoding="utf-8"))
        # Только Old и Mid (до 2025-06-01)
        msg_ids = [m["id"] for m in data["messages"]]
        assert 1 in msg_ids
        assert 2 in msg_ids
        assert 3 not in msg_ids


class TestExportDateRange(TestCliCommandBase):
    """Тесты комбинации --date-from + --date-to."""

    def _setup_chat_with_dated_messages(self):
        user = make_fake_user(id=1, username="u")
        chat = make_fake_chat(id=-1001234, title="Range Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Range Chat", entity=chat)
        msgs = [
            make_fake_message(msg_id=1, text="Jan",
                              date=datetime(2025, 1, 15, tzinfo=UTC)),
            make_fake_message(msg_id=2, text="Mar",
                              date=datetime(2025, 3, 15, tzinfo=UTC)),
            make_fake_message(msg_id=3, text="Jun",
                              date=datetime(2025, 6, 15, tzinfo=UTC)),
            make_fake_message(msg_id=4, text="Sep",
                              date=datetime(2025, 9, 15, tzinfo=UTC)),
        ]
        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(-1001234, msgs)

    def test_date_range_filters_both_ends(self, tmp_path: Path):
        """--date-from + --date-to фильтрует с обеих сторон."""
        self._setup_chat_with_dated_messages()

        result = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "json", "--date-from", "2025-02-01", "--date-to", "2025-08-01",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("Range_Chat_*"))
        data = json.loads((export_dirs[0] / "result.json").read_text(encoding="utf-8"))
        msg_ids = [m["id"] for m in data["messages"]]
        # Только Mar (3) и Jun (4) попадают в диапазон
        assert 2 in msg_ids
        assert 3 in msg_ids
        assert 1 not in msg_ids
        assert 4 not in msg_ids


class TestExportDays(TestCliCommandBase):
    """Тесты атрибута --days."""

    def _setup_chat_with_dated_messages(self):
        user = make_fake_user(id=1, username="u")
        chat = make_fake_chat(id=-1001234, title="Days Chat")
        dialog = make_fake_dialog(dialog_id=-1001234, name="Days Chat", entity=chat)
        now = datetime.now(UTC)
        msgs = [
            make_fake_message(msg_id=1, text="Today", date=now),
            make_fake_message(msg_id=2, text="Yesterday",
                              date=now - timedelta(days=1)),
            make_fake_message(msg_id=3, text="3 days ago",
                              date=now - timedelta(days=3)),
            make_fake_message(msg_id=4, text="10 days ago",
                              date=now - timedelta(days=10)),
            make_fake_message(msg_id=5, text="30 days ago",
                              date=now - timedelta(days=30)),
        ]
        self.server.users.add_user(user)
        self.server.dialogs.add_dialog(dialog)
        self.server.messages.add_messages(-1001234, msgs)

    def test_days_filters_by_period(self, tmp_path: Path):
        """--days 2 экспортирует сообщения за последние 2 дня."""
        self._setup_chat_with_dated_messages()

        result = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--format", "json", "--days", "2",
        )
        assert result.exit_code == 0, f"STDERR: {result.stderr}"

        export_dirs = list(tmp_path.glob("Days_Chat_*"))
        data = json.loads((export_dirs[0] / "result.json").read_text(encoding="utf-8"))
        msg_ids = [m["id"] for m in data["messages"]]
        # Today и Yesterday (последние 2 дня)
        assert 1 in msg_ids
        assert 2 in msg_ids
        assert 3 not in msg_ids  # 3 days ago
        assert 4 not in msg_ids  # 10 days ago
        assert 5 not in msg_ids  # 30 days ago

    def test_days_conflicts_with_date_from(self, tmp_path: Path):
        """--days нельзя комбинировать с --date-from."""
        result = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--days", "7", "--date-from", "2025-01-01",
        )
        assert result.exit_code != 0

    def test_days_conflicts_with_date_to(self, tmp_path: Path):
        """--days нельзя комбинировать с --date-to."""
        result = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--days", "7", "--date-to", "2025-01-15",
        )
        assert result.exit_code != 0


class TestExportInvalidDate(TestCliCommandBase):
    """Тесты валидации формата дат."""

    def test_invalid_date_format_returns_error(self, tmp_path: Path):
        """Неверный формат даты вызывает ошибку."""
        result = self._invoke(
            "export", "--chat", "-1001234", "--output", str(tmp_path),
            "--date-from", "01-01-2025",
        )
        assert result.exit_code != 0
