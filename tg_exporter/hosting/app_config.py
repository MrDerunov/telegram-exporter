"""
AppConfig — конфигурация приложения (frozen, только поля).

Все секреты приходят из CliConfig через config_mapper.
Загрузкой/сохранением занимается app_config_repository.
Валидацией занимается app_config_validator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..services.export.markdown_settings import MarkdownSettings


@dataclass(frozen=True)
class AppConfig:
    # Telegram API
    api_id: str = ""
    api_hash: str = ""

    # Транскрипция
    transcription_provider: str = "local"
    transcription_language: str = "multi"
    local_whisper_model: str = "base"
    deepgram_api_key: str = ""

    # Интерфейс
    include_private_chats: bool = False

    # Настройки Markdown
    markdown: MarkdownSettings = field(default_factory=MarkdownSettings)

    @property
    def api_id_int(self) -> Optional[int]:
        """Возвращает api_id как int, или None если не задан / невалиден."""
        digits = "".join(c for c in self.api_id if c.isdigit())
        return int(digits) if digits else None

    # ---- Сериализация ----

    def to_dict(self) -> dict:
        """Только несекретные поля — safe для записи в файл."""
        return {
            "api_id": self.api_id,
            "api_hash": self.api_hash,
            "transcription_provider": self.transcription_provider,
            "transcription_language": self.transcription_language,
            "local_whisper_model": self.local_whisper_model,
            "deepgram_api_key": self.deepgram_api_key,
            "include_private_chats": self.include_private_chats,
            "markdown": self.markdown.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        md_data = data.pop("markdown", {})
        known = {f for f in cls.__dataclass_fields__ if f != "markdown"}
        filtered = {k: v for k, v in data.items() if k in known}
        obj = cls(**filtered)
        if md_data:
            obj = _replace_attr(obj, "markdown", MarkdownSettings.from_dict(md_data))
        return obj

    def with_api_id(self, api_id: str) -> "AppConfig":
        """Возвращает новый экземпляр с обновлённым api_id."""
        digits = "".join(c for c in (api_id or "") if c.isdigit())
        import dataclasses
        return dataclasses.replace(self, api_id=digits)


def _replace_attr(obj: AppConfig, name: str, value) -> AppConfig:
    """dataclasses.replace для frozen AppConfig."""
    import dataclasses
    return dataclasses.replace(obj, **{name: value})
