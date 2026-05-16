"""
ExportTask — описание задачи экспорта.

Параметры задачи иммутабельны после создания.
Прогресс обновляется через ExportProgress (отдельный изменяемый объект).
"""

from __future__ import annotations

import dataclasses
import datetime
from dataclasses import dataclass, field

from tg_exporter.services.export.models.author_filter import AuthorFilter
from tg_exporter.services.export.models.export_format import ExportFormat


@dataclass(frozen=True)
class ExportTask:
    """
    Параметры задачи экспорта. Иммутабелен — создаётся один раз перед запуском.

    Содержит только то что нужно знать до начала экспорта.
    Прогресс хранится отдельно в ExportProgress.
    """

    # Идентификатор чата
    chat_id: int
    chat_name: str

    # Куда писать результат
    output_path: str

    # Формат экспорта
    format: ExportFormat = ExportFormat.BOTH

    # Фильтрация по дате
    date_from: datetime.datetime | None = None
    date_to: datetime.datetime | None = None

    # Топик (для форумов)
    topic_id: int | None = None
    topic_title: str | None = None

    # Медиа
    download_media: bool = False

    # Аналитика
    collect_analytics: bool = False

    # Транскрипция
    transcribe_audio: bool = False
    transcription_provider: str = "local"
    transcription_language: str = "multi"
    local_whisper_model: str = "base"
    deepgram_api_key: str = ""

    # Фильтр авторов
    author_filter: AuthorFilter = field(default_factory=AuthorFilter)

    # Инкрементальный экспорт (только новые сообщения)
    incremental: bool = False
    last_exported_id: int | None = None  # для инкрементального

    # Лимит сообщений (0 = без лимита)
    message_limit: int = 0

    # Настройки Markdown
    words_per_file: int = 50_000

    def with_last_id(self, last_id: int) -> ExportTask:
        return dataclasses.replace(self, last_exported_id=last_id)

    @property
    def is_incremental_with_offset(self) -> bool:
        return self.incremental and self.last_exported_id is not None
