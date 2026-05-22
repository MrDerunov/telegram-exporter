"""Константы ключей для SecretProvider. Единый источник имён."""
from __future__ import annotations

# Префикс для переменных окружения и .env файлов
_ENV_PREFIX = "TG_EXPORTER_"

# Ключи секретов (без префикса — EnvVarsSecretProvider добавляет _ENV_PREFIX)
API_HASH = "API_HASH"
API_ID = "API_ID"
SESSION = "SESSION"
DEEPGRAM_API_KEY = "DEEPGRAM_API_KEY"

# Полные имена переменных окружения (с префиксом)
API_HASH_ENV = f"{_ENV_PREFIX}API_HASH"
API_ID_ENV = f"{_ENV_PREFIX}API_ID"
SESSION_ENV = f"{_ENV_PREFIX}SESSION"
DEEPGRAM_API_KEY_ENV = f"{_ENV_PREFIX}DEEPGRAM_API_KEY"
