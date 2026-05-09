"""Тесты ExportHistory — инкрементальный экспорт (новый per-chat API)."""
from __future__ import annotations

import json
import datetime
from pathlib import Path
import pytest

from tg_exporter.services.export_history import ExportHistory, _HISTORY_FILENAME


class TestExportHistoryLoad:
    def test_load_returns_none_when_no_file(self, tmp_path: Path):
        """Если файла нет — load() возвращает None."""
        result = ExportHistory.load(tmp_path)
        assert result is None

    def test_load_returns_data_when_file_exists(self, tmp_path: Path):
        """Если файл есть — возвращает dict."""
        hist_path = tmp_path / _HISTORY_FILENAME
        hist_path.write_text(json.dumps({"last_message_id": 100}))
        result = ExportHistory.load(tmp_path)
        assert result == {"last_message_id": 100}

    def test_load_returns_none_on_corrupted_file(self, tmp_path: Path):
        """Повреждённый JSON — возвращает None без падения."""
        hist_path = tmp_path / _HISTORY_FILENAME
        hist_path.write_text("not json {{{")
        result = ExportHistory.load(tmp_path)
        assert result is None


class TestExportHistoryMarkers:
    def test_mark_completed(self, tmp_path: Path):
        """mark_completed() создаёт файл с правильными данными."""
        ExportHistory.mark_completed(tmp_path, 500, 1200)
        data = ExportHistory.load(tmp_path)
        assert data is not None
        assert data["last_message_id"] == 500
        assert data["total_exported"] == 1200
        assert data["status"] == "completed"
        assert data["interrupted"] is False
        assert "last_export_date" in data

    def test_mark_interrupted(self, tmp_path: Path):
        """mark_interrupted() создаёт файл с interrupted=True."""
        ExportHistory.mark_interrupted(tmp_path, 300, 800)
        data = ExportHistory.load(tmp_path)
        assert data is not None
        assert data["status"] == "interrupted"
        assert data["interrupted"] is True

    def test_mark_unavailable(self, tmp_path: Path):
        """mark_unavailable() создаёт файл со статусом unavailable."""
        ExportHistory.mark_unavailable(tmp_path)
        data = ExportHistory.load(tmp_path)
        assert data is not None
        assert data["status"] == "unavailable"
        assert data["total_exported"] == 0

    def test_save_overwrites_previous(self, tmp_path: Path):
        """Повторный save перезаписывает данные."""
        ExportHistory.mark_completed(tmp_path, 100, 200)
        ExportHistory.mark_completed(tmp_path, 999, 5000)
        data = ExportHistory.load(tmp_path)
        assert data is not None
        assert data["last_message_id"] == 999

    def test_atomic_write_does_not_leave_tmp(self, tmp_path: Path):
        """После save не остаётся .tmp файла."""
        ExportHistory.mark_completed(tmp_path, 1, 10)
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []


class TestExportHistoryExportHistoryClass:
    def test_instantiable_without_args(self):
        """ExportHistory можно создать без аргументов."""
        h = ExportHistory()
        assert h is not None

    def test_load_from_nonexistent_dir(self, tmp_path: Path):
        """Несуществующая директория — load() возвращает None без падения."""
        result = ExportHistory.load(tmp_path / "nonexistent")
        assert result is None
