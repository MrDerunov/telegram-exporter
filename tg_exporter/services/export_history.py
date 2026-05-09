"""
ExportHistory — хранит историю экспорта для каждого чата.

Файл: {output_dir}/export_history.json (на каждый чат свой, в папке экспорта).
Используется для инкрементального экспорта (--resume) и отслеживания статуса.
"""
from __future__ import annotations

import json
import datetime
from pathlib import Path
from typing import Optional


_HISTORY_FILENAME = "export_history.json"


class ExportHistory:
    """Персистентное хранилище состояния экспорта для одного чата."""

    def __init__(self) -> None:
        # Экземпляр без состояния — все методы принимают output_dir
        pass

    @staticmethod
    def load(output_dir: Path) -> Optional[dict]:
        """Загружает историю экспорта из папки чата. Возвращает None если файла нет."""
        hist_path = output_dir / _HISTORY_FILENAME
        if not hist_path.exists():
            return None
        try:
            with hist_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def save(output_dir: Path, data: dict) -> None:
        """Сохраняет данные истории в папку чата."""
        from tg_exporter.utils.file_utils import atomic_write
        hist_path = output_dir / _HISTORY_FILENAME
        atomic_write(hist_path, json.dumps(data, indent=2, ensure_ascii=False))

    @staticmethod
    def mark_completed(output_dir: Path, last_id: int, total: int) -> None:
        """Отметить экспорт как успешно завершённый."""
        ExportHistory.save(output_dir, {
            "last_message_id": last_id,
            "last_export_date": datetime.datetime.now().isoformat(),
            "total_exported": total,
            "status": "completed",
            "interrupted": False,
        })

    @staticmethod
    def mark_interrupted(output_dir: Path, last_id: int, total: int) -> None:
        """Отметить экспорт как прерванный (для --resume)."""
        ExportHistory.save(output_dir, {
            "last_message_id": last_id,
            "last_export_date": datetime.datetime.now().isoformat(),
            "total_exported": total,
            "status": "interrupted",
            "interrupted": True,
        })

    @staticmethod
    def mark_unavailable(output_dir: Path) -> None:
        """Отметить чат как недоступный."""
        ExportHistory.save(output_dir, {
            "last_message_id": 0,
            "last_export_date": datetime.datetime.now().isoformat(),
            "total_exported": 0,
            "status": "unavailable",
            "interrupted": False,
        })
