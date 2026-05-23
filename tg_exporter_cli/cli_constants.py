"""Константы CLI-приложения."""
from __future__ import annotations

# Версия из _version.py (генерируется скриптом сборки / CI из git-тега).
# Если файла нет (dev-режим) — fallback на "0.0.0".
try:
    from tg_exporter_cli._version import VERSION as _version_from_build
    VERSION = _version_from_build
except ImportError:
    VERSION = "0.0.0"

DEFAULT_ENV_FILENAME = ".env"
DEFAULT_SECRETS_EXPORTED_ENV_FILENAME = "secrets.exported.env"
DEFAULT_PROFILE_NAME = "Default"
