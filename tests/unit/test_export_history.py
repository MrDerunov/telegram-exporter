"""Тесты ExportHistory — инкрементальный экспорт."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from tg_exporter.services.export_history import ExportHistory


# ---------------------------------------------------------------------------
# Базовое сохранение / загрузка
# ---------------------------------------------------------------------------

class TestExportHistorySaveLoad:
    def test_save_and_load(self, tmp_path: Path):
        """Сохранение данных для нескольких чатов и их загрузка."""
        hist_file = tmp_path / "export_history.json"
        h1 = ExportHistory(path=hist_file)
        h1.set_last_id(peer_id=-1001234, message_id=100)
        h1.set_last_id(peer_id=-1005678, message_id=200)

        # Перезагружаем из того же файла
        h2 = ExportHistory(path=hist_file)
        assert h2.get_last_id(-1001234) == 100
        assert h2.get_last_id(-1005678) == 200

    def test_get_last_id_returns_none_for_unknown_peer(self, tmp_path: Path):
        """Неизвестный peer_id → None."""
        hist = ExportHistory(path=tmp_path / "export_history.json")
        assert hist.get_last_id(999999) is None

    def test_set_last_id_only_increases(self, tmp_path: Path):
        """set_last_id не уменьшает значение — только увеличивает."""
        hist = ExportHistory(path=tmp_path / "export_history.json")
        hist.set_last_id(peer_id=-100, message_id=500)
        hist.set_last_id(peer_id=-100, message_id=300)  # меньше → не сохраняется
        assert hist.get_last_id(-100) == 500

    def test_set_last_id_higher_updates(self, tmp_path: Path):
        """Большее значение перезаписывает меньшее."""
        hist = ExportHistory(path=tmp_path / "export_history.json")
        hist.set_last_id(peer_id=-100, message_id=100)
        hist.set_last_id(peer_id=-100, message_id=999)
        assert hist.get_last_id(-100) == 999

    def test_clear_removes_peer(self, tmp_path: Path):
        """clear() удаляет запись конкретного чата."""
        hist = ExportHistory(path=tmp_path / "export_history.json")
        hist.set_last_id(peer_id=-100, message_id=42)
        hist.clear(-100)
        assert hist.get_last_id(-100) is None

    def test_clear_nonexistent_does_not_crash(self, tmp_path: Path):
        """clear() для отсутствующего peer_id не ломается."""
        hist = ExportHistory(path=tmp_path / "export_history.json")
        hist.clear(999)  # не должен кидать исключение


# ---------------------------------------------------------------------------
# Отсутствующий файл истории
# ---------------------------------------------------------------------------

class TestExportHistoryNoFile:
    def test_no_history_returns_none(self, tmp_path: Path):
        """Если файла истории нет — get_last_id возвращает None."""
        hist = ExportHistory(path=tmp_path / "nonexistent.json")
        assert hist.get_last_id(-100) is None

    def test_no_history_does_not_crash(self, tmp_path: Path):
        """Создание ExportHistory без существующего файла не падает."""
        hist = ExportHistory(path=tmp_path / "nonexistent.json")
        # Можно вызвать set_last_id — файл создастся
        hist.set_last_id(peer_id=1, message_id=10)
        assert hist.get_last_id(1) == 10


# ---------------------------------------------------------------------------
# Повреждённый JSON
# ---------------------------------------------------------------------------

class TestExportHistoryCorruptedFile:
    def test_corrupted_json_does_not_crash(self, tmp_path: Path):
        """Повреждённый JSON обрабатывается без исключений."""
        hist_file = tmp_path / "export_history.json"
        hist_file.write_text("не json {{{")
        hist = ExportHistory(path=hist_file)
        # Внутреннее _load() должно поймать исключение и установить _data = {}
        assert hist.get_last_id(1) is None

    def test_empty_file_does_not_crash(self, tmp_path: Path):
        """Пустой файл — не проблема."""
        hist_file = tmp_path / "export_history.json"
        hist_file.write_text("")
        hist = ExportHistory(path=hist_file)
        assert hist.get_last_id(1) is None

    def test_non_integer_values_are_ignored(self, tmp_path: Path):
        """Нечисловые значения игнорируются при загрузке."""
        hist_file = tmp_path / "export_history.json"
        hist_file.write_text(json.dumps({"-100": "not_a_number", "-200": "123"}))
        hist = ExportHistory(path=hist_file)
        # "123" — isdigit, должно загрузиться как int
        assert hist.get_last_id(-200) == 123
        # "not_a_number" — не isdigit, игнорируется
        assert hist.get_last_id(-100) is None


# ---------------------------------------------------------------------------
# Атомарная запись
# ---------------------------------------------------------------------------

class TestExportHistoryAtomicWrite:
    def test_tmp_file_cleaned_up(self, tmp_path: Path):
        """После сохранения временный файл не остаётся."""
        hist = ExportHistory(path=tmp_path / "export_history.json")
        hist.set_last_id(peer_id=1, message_id=100)
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_result_file_is_valid_json(self, tmp_path: Path):
        """Результирующий файл всегда валидный JSON."""
        hist_file = tmp_path / "export_history.json"
        hist = ExportHistory(path=hist_file)
        hist.set_last_id(peer_id=1, message_id=42)
        data = json.loads(hist_file.read_text())
        assert data["1"] == 42
