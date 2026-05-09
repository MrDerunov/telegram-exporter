"""CliConfig — конфигурация CLI-приложения.
Хранится в ~/.tg_exporter/cli_config.yaml.
Не содержит секретов — они через SecretProvider.
Загрузкой/сохранением занимается cli_config_repository.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_DIR = Path.home() / ".tg_exporter"
DEFAULT_CONFIG_FILENAME = "cli_config.yaml"
DEFAULT_ENV_FILENAME = ".env"
DEFAULT_SECRETS_ENV_FILENAME = "secrets.env"


@dataclass
class ChatEntry:
    """Запись о чате в конфиге."""
    name: str
    id: int


@dataclass
class CliConfig:
    version: int = 1
    api_id: str = ""
    default_profile: str = "default"

    # Список чатов для быстрого доступа (chats add/remove)
    chats: list[ChatEntry] = field(default_factory=list)

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
