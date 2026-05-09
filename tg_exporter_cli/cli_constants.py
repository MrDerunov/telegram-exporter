"""Константы CLI-приложения."""
from __future__ import annotations
from pathlib import Path

VERSION = "1.0.0"

# Директория и файлы конфигурации
CONFIG_DIR = Path.home() / ".tg_exporter"
CONFIG_FILENAME = "cli_config.yaml"
DEFAULT_ENV_FILENAME = ".env"
DEFAULT_SECRETS_ENV_FILENAME = "secrets.env"
