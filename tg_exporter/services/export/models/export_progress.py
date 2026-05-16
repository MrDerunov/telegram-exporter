"""
ExportProgress — изменяемое состояние выполнения задачи экспорта.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from tg_exporter.services.export.models.export_format import ExportStatus


@dataclass
class ExportProgress:
    """
    Изменяемое состояние выполнения задачи.
    Обновляется в фоновом потоке, читается UI-потоком через очередь.
    """

    status: ExportStatus = ExportStatus.PENDING

    # Счётчики сообщений
    total_messages: int = 0          # известно не сразу — 0 пока не определено
    processed_messages: int = 0
    skipped_messages: int = 0

    # Медиа
    media_downloaded: int = 0
    media_failed: int = 0

    # Файлы вывода
    output_files: list[str] = field(default_factory=list)

    # Ошибки
    error: str | None = None
    warnings: list[str] = field(default_factory=list)

    # Время
    started_at: datetime.datetime | None = None
    finished_at: datetime.datetime | None = None

    def start(self) -> None:
        self.status = ExportStatus.RUNNING
        self.started_at = datetime.datetime.now()

    def finish(self) -> None:
        self.status = ExportStatus.DONE
        self.finished_at = datetime.datetime.now()

    def cancel(self) -> None:
        self.status = ExportStatus.CANCELLED
        self.finished_at = datetime.datetime.now()

    def fail(self, error: str) -> None:
        self.status = ExportStatus.ERROR
        self.error = error
        self.finished_at = datetime.datetime.now()

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def add_output_file(self, path: str) -> None:
        if path not in self.output_files:
            self.output_files.append(path)

    @property
    def elapsed_seconds(self) -> float | None:
        if self.started_at is None:
            return None
        end = self.finished_at or datetime.datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def progress_ratio(self) -> float | None:
        """0.0–1.0, или None если total неизвестен."""
        if self.total_messages <= 0:
            return None
        return min(self.processed_messages / self.total_messages, 1.0)

    @property
    def messages_per_second(self) -> float | None:
        elapsed = self.elapsed_seconds
        if not elapsed or self.processed_messages == 0:
            return None
        return self.processed_messages / elapsed

    @property
    def eta_seconds(self) -> float | None:
        """Оценка оставшегося времени в секундах."""
        ratio = self.progress_ratio
        elapsed = self.elapsed_seconds
        if ratio is None or ratio <= 0 or elapsed is None:
            return None
        if ratio >= 1.0:
            return 0.0
        return elapsed / ratio * (1.0 - ratio)
