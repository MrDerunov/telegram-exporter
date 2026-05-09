"""CliConfig — конфигурация CLI-приложения.
Хранится в ~/.tg_exporter/cli_config.yaml.
Не содержит секретов — они через SecretProvider.
Загрузкой/сохранением занимается cli_config_repository.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_DIR = Path.home() / ".tg_exporter"


@dataclass
class CliConfig:
    version: int = 1
    api_id: str = ""
    default_profile: str = "default"
    # Retry settings
    retry_max_attempts: int = 3
    retry_delay_seconds: int = 2
    retry_max_delay_seconds: int = 60
    # Rate limiting
    rate_limit_media_download_delay_ms: int = 500
    rate_limit_message_fetch_delay_ms: int = 100
