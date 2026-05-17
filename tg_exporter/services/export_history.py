"""
ExportHistory — хранит историю экспорта для каждого чата.

Файл: {output_dir}/export_history.json (на каждый чат свой, в папке экспорта).
Используется для инкрементального экспорта (--resume) и отслеживания статуса.
"""
from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from pathlib import Path

from tg_exporter.utils.file_utils import atomic_write


_HISTORY_FILENAME = "export_history.json"


@dataclass(frozen=True)
class ExportHistoryRecord:
    """Состояние экспорта для одного чата."""

    last_message_id: int = 0
    last_export_date: str = ""
    total_exported: int = 0
    status: str = ""          # "completed", "interrupted", "unavailable"
    interrupted: bool = False

    def to_dict(self) -> dict:
        return {
            "last_message_id": self.last_message_id,
            "last_export_date": self.last_export_date,
            "total_exported": self.total_exported,
            "status": self.status,
            "interrupted": self.interrupted,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ExportHistoryRecord:
        return cls(
            last_message_id=data.get("last_message_id", 0),
            last_export_date=data.get("last_export_date", ""),
            total_exported=data.get("total_exported", 0),
            status=data.get("status", ""),
            interrupted=data.get("interrupted", False),
        )


class ExportHistory:
    """Персистентное хранилище состояния экспорта для одного чата."""

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # load / save
    # ------------------------------------------------------------------

    @staticmethod
    def load(output_dir: Path) -> ExportHistoryRecord | None:
        """Загружает историю экспорта из папки чата. Возвращает None если файла нет."""
        hist_path = output_dir / _HISTORY_FILENAME
        if not hist_path.exists():
            return None
        try:
            with hist_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return ExportHistoryRecord.from_dict(data)
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def save(output_dir: Path, record: ExportHistoryRecord) -> None:
        """Сохраняет запись истории в папку чата."""
        hist_path = output_dir / _HISTORY_FILENAME
        atomic_write(hist_path, json.dumps(record.to_dict(), indent=2, ensure_ascii=False))

    # ------------------------------------------------------------------
    # mark_* — фабрики записей с автосохранением
    # ------------------------------------------------------------------

    @staticmethod
    def mark_completed(output_dir: Path, last_id: int, total: int) -> None:
        """Отметить экспорт как успешно завершённый."""
        record = ExportHistoryRecord(
            last_message_id=last_id,
            last_export_date=datetime.datetime.now().isoformat(),
            total_exported=total,
            status="completed",
            interrupted=False,
        )
        ExportHistory.save(output_dir, record)

    @staticmethod
    def mark_interrupted(output_dir: Path, last_id: int, total: int) -> None:
        """Отметить экспорт как прерванный (для --resume)."""
        record = ExportHistoryRecord(
            last_message_id=last_id,
            last_export_date=datetime.datetime.now().isoformat(),
            total_exported=total,
            status="interrupted",
            interrupted=True,
        )
        ExportHistory.save(output_dir, record)

    @staticmethod
    def mark_unavailable(output_dir: Path) -> None:
        """Отметить чат как недоступный."""
        record = ExportHistoryRecord(
            last_message_id=0,
            last_export_date=datetime.datetime.now().isoformat(),
            total_exported=0,
            status="unavailable",
            interrupted=False,
        )
        ExportHistory.save(output_dir, record)
