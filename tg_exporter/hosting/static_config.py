"""StaticConfig — статическая конфигурация приложения (frozen).
Задаётся до старта, не меняется в рантайме.
Заменяет AppConfig + статические поля CliConfig.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from tg_exporter.services.export.markdown_settings import MarkdownSettings


@dataclass(frozen=True)
class StaticConfig:
    version: int = 1
    api_id: str = ""
    api_hash: str = ""              # из секретов при мердже
    deepgram_api_key: str = ""      # из секретов при мердже

    # Транскрипция
    transcription_provider: str = "local"
    transcription_model: str = "base"
    transcription_language: str = "multi"

    # Экспорт по умолчанию
    default_format: str = "both"
    default_words_per_file: int = 50000
    default_download_media: bool = False
    default_transcribe: bool = False
    default_analytics: bool = False
    include_private_chats: bool = False
    default_profile: str = "default"

    # Markdown
    markdown: MarkdownSettings = field(default_factory=MarkdownSettings)

    # Источник секретов: "keyring" или "file"
    secrets_source: str = "file"

    # Логирование
    log_level: str = "INFO"

    # Retry
    retry_max_attempts: int = 3
    retry_delay_seconds: int = 2
    retry_max_delay_seconds: int = 60

    # Rate limit
    rate_limit_media_download_delay_ms: int = 500
    rate_limit_message_fetch_delay_ms: int = 100

    @property
    def api_id_int(self) -> int | None:
        """Возвращает api_id как int, или None если не задан / невалиден."""
        digits = "".join(c for c in self.api_id if c.isdigit())
        return int(digits) if digits else None

    @classmethod
    def from_raw(cls, data: dict) -> StaticConfig:
        """Собирает StaticConfig из словаря (плоского или с вложенными ключами)."""
        retry = data.get("retry", {}) or {}
        rate = data.get("rate_limit", {}) or {}
        transcription = data.get("transcription", {}) or {}
        logging_data = data.get("logging", {}) or {}
        defaults = data.get("defaults", {}) or {}
        markdown_data = data.get("markdown", {}) or {}

        md = MarkdownSettings.from_dict(markdown_data) if markdown_data else MarkdownSettings()

        return cls(
            version=int(data.get("version", 1)),
            api_id=str(data.get("api_id", "")),
            api_hash=str(data.get("api_hash", "")),
            deepgram_api_key=str(data.get("deepgram_api_key", "")),
            transcription_provider=str(transcription.get("provider", "local")),
            transcription_model=str(transcription.get("model", "base")),
            transcription_language=str(transcription.get("language", "multi")),
            default_format=str(defaults.get("format", "both")),
            default_words_per_file=int(defaults.get("words_per_file", 50000)),
            default_download_media=bool(defaults.get("download_media", False)),
            default_transcribe=bool(defaults.get("transcribe", False)),
            default_analytics=bool(defaults.get("analytics", False)),
            include_private_chats=bool(data.get("include_private_chats", False)),
            default_profile=str(data.get("default_profile", "default")),
            markdown=md,
            secrets_source=str(data.get("secrets_source", "file")),
            log_level=str(logging_data.get("level", "INFO")),
            retry_max_attempts=int(retry.get("max_attempts", 3)),
            retry_delay_seconds=int(retry.get("delay_seconds", 2)),
            retry_max_delay_seconds=int(retry.get("max_delay_seconds", 60)),
            rate_limit_media_download_delay_ms=int(rate.get("media_download_delay_ms", 500)),
            rate_limit_message_fetch_delay_ms=int(rate.get("message_fetch_delay_ms", 100)),
        )
