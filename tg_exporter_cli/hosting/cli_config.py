"""CliConfig — конфигурация CLI-приложения (frozen).
Хранится в ~/.tg-exporter/cli_config.yaml.
Секреты (api_hash, deepgram_api_key) не сериализуются в YAML —
они читаются через SecretProvider при _configure_cli.
Загрузкой/сохранением занимается cli_config_repository.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from tg_exporter_cli.cli_constants import (
    CONFIG_DIR,
    CONFIG_FILENAME,
    DEFAULT_ENV_FILENAME,
    DEFAULT_SECRETS_ENV_FILENAME,
)

# Реэкспорт для обратной совместимости
DEFAULT_CONFIG_DIR = CONFIG_DIR
DEFAULT_CONFIG_FILENAME = CONFIG_FILENAME


@dataclass(frozen=True)
class ChatEntry:
    """Запись о чате в конфиге."""
    name: str
    id: int


@dataclass(frozen=True)
class CliConfig:
    version: int = 1
    api_id: str = ""
    api_hash: str = ""
    default_profile: str = "default"

    # Список чатов для быстрого доступа (chats add/remove)
    chats: tuple[ChatEntry, ...] = field(default_factory=tuple)

    # Настройки по умолчанию для экспорта
    default_format: str = "both"
    default_words_per_file: int = 50000
    default_download_media: bool = False
    default_transcribe: bool = False
    default_analytics: bool = False

    # Транскрипция
    transcription_provider: str = "local"
    transcription_model: str = "base"
    transcription_language: str = "multi"

    # Секреты (не сериализуются в YAML)
    deepgram_api_key: str = ""

    # Источник секретов
    secrets_source: str = "chain"

    # Логирование
    log_level: str = "INFO"
    log_file: str = ""

    # Retry settings
    retry_max_attempts: int = 3
    retry_delay_seconds: int = 2
    retry_max_delay_seconds: int = 60

    # Rate limiting
    rate_limit_media_download_delay_ms: int = 500
    rate_limit_message_fetch_delay_ms: int = 100

    @classmethod
    def from_raw(cls, data: dict) -> CliConfig:
        """Собирает CliConfig из словаря (плоского или с вложенными ключами)."""
        retry = data.get("retry", {}) or {}
        rate = data.get("rate_limit", {}) or {}
        transcription = data.get("transcription", {}) or {}
        logging_data = data.get("logging", {}) or {}
        defaults = data.get("defaults", {}) or {}

        chats_raw = data.get("chats", []) or []
        chats = tuple(
            ChatEntry(name=c["name"], id=c["id"])
            for c in chats_raw
            if isinstance(c, dict)
        )

        return cls(
            version=data.get("version", 1),
            api_id=str(data.get("api_id", "")),
            api_hash=str(data.get("api_hash", "")),
            default_profile=str(data.get("default_profile", "default")),
            chats=chats,
            default_format=str(defaults.get("format", "both")),
            default_words_per_file=int(defaults.get("words_per_file", 50000)),
            default_download_media=bool(defaults.get("download_media", False)),
            default_transcribe=bool(defaults.get("transcribe", False)),
            default_analytics=bool(defaults.get("analytics", False)),
            transcription_provider=str(transcription.get("provider", "local")),
            transcription_model=str(transcription.get("model", "base")),
            transcription_language=str(transcription.get("language", "multi")),
            deepgram_api_key=str(data.get("deepgram_api_key", "")),
            secrets_source=str(data.get("secrets_source", "chain")),
            log_level=str(logging_data.get("level", "INFO")),
            log_file=str(logging_data.get("file", "")),
            retry_max_attempts=int(retry.get("max_attempts", 3)),
            retry_delay_seconds=int(retry.get("delay_seconds", 2)),
            retry_max_delay_seconds=int(retry.get("max_delay_seconds", 60)),
            rate_limit_media_download_delay_ms=int(rate.get("media_download_delay_ms", 500)),
            rate_limit_message_fetch_delay_ms=int(rate.get("message_fetch_delay_ms", 100)),
        )
