"""Тесты ExportHistory — инкрементальный экспорт (новый per-chat API)."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from tg_exporter.services.export_history import ExportHistory, ExportHistoryRecord, _HISTORY_FILENAME


class TestExportHistoryRecord:

    def test_to_dict_roundtrip(self):
        """to_dict и from_dict обратимы."""
        record = ExportHistoryRecord(
            last_message_id=500,
            last_export_date="2024-06-15T10:00:00",
            total_exported=1200,
            status="completed",
            interrupted=False,
        )
        data = record.to_dict()
        restored = ExportHistoryRecord.from_dict(data)
        assert restored == record



class TestExportHistoryLoad:
    def test_return_none_when_file_does_not_exist(self, tmp_path: Path):
        """Если файла нет — load() возвращает None."""
        result = ExportHistory.load(tmp_path)
        assert result is None

    def test_return_record_when_file_exists(self, tmp_path: Path):
        """Если файл есть — возвращает ExportHistoryRecord."""
        hist_path = tmp_path / _HISTORY_FILENAME
        hist_path.write_text(json.dumps({"last_message_id": 100}))
        result = ExportHistory.load(tmp_path)
        assert isinstance(result, ExportHistoryRecord)
        assert result.last_message_id == 100

    def test_return_none_on_corrupted_file(self, tmp_path: Path):
        """Повреждённый JSON — возвращает None без падения."""
        hist_path = tmp_path / _HISTORY_FILENAME
        hist_path.write_text("not json {{{")
        result = ExportHistory.load(tmp_path)
        assert result is None


class TestExportHistoryMarkers:
    def test_mark_completed_creates_record(self, tmp_path: Path):
        """mark_completed() создаёт запись с правильными данными."""
        ExportHistory.mark_completed(tmp_path, 500, 1200)
        record = ExportHistory.load(tmp_path)
        assert record is not None
        assert record.last_message_id == 500
        assert record.total_exported == 1200
        assert record.status == "completed"
        assert record.interrupted is False
        assert record.last_export_date != ""

    def test_mark_interrupted_creates_record(self, tmp_path: Path):
        """mark_interrupted() создаёт запись с interrupted=True."""
        ExportHistory.mark_interrupted(tmp_path, 300, 800)
        record = ExportHistory.load(tmp_path)
        assert record is not None
        assert record.status == "interrupted"
        assert record.interrupted is True

    def test_mark_unavailable_creates_record(self, tmp_path: Path):
        """mark_unavailable() создаёт запись со статусом unavailable."""
        ExportHistory.mark_unavailable(tmp_path)
        record = ExportHistory.load(tmp_path)
        assert record is not None
        assert record.status == "unavailable"
        assert record.total_exported == 0

    def test_save_overwrites_previous_record(self, tmp_path: Path):
        """Повторный save перезаписывает данные."""
        ExportHistory.mark_completed(tmp_path, 100, 200)
        ExportHistory.mark_completed(tmp_path, 999, 5000)
        record = ExportHistory.load(tmp_path)
        assert record is not None
        assert record.last_message_id == 999

    def test_atomic_write_does_not_leave_tmp(self, tmp_path: Path):
        """После save не остаётся .tmp файла."""
        ExportHistory.mark_completed(tmp_path, 1, 10)
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []
