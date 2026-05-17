"""EnvFallbackSecretStore — враппер: сначала переменные окружения, затем вложенный store."""

from __future__ import annotations

import os

from tg_exporter.secrets.secret_store import ISecretStore
from tg_exporter.secrets.secret_keys import (
    API_ID, API_HASH, SESSION, DEEPGRAM_API_KEY,
    API_ID_ENV, API_HASH_ENV, SESSION_ENV, DEEPGRAM_API_KEY_ENV,
)


# Маппинг ключей SecretStore → переменные окружения
_ENV_MAP: dict[str, str] = {
    SESSION: SESSION_ENV,
    API_ID: API_ID_ENV,
    API_HASH: API_HASH_ENV,
    DEEPGRAM_API_KEY: DEEPGRAM_API_KEY_ENV,
}


class EnvFallbackSecretStore(ISecretStore):
    """Враппер над ISecretStore с fallback-чтением из переменных окружения.

    get(): сначала os.environ, затем inner store.
    set() / delete(): делегирует напрямую в inner store.
    """

    def __init__(self, inner: ISecretStore) -> None:
        self._inner = inner

    def get(self, key: str) -> str | None:
        env_var = _ENV_MAP.get(key)
        if env_var:
            value = os.environ.get(env_var)
            if value is not None:
                return value
        return self._inner.get(key)

    def set(self, key: str, value: str) -> None:
        self._inner.set(key, value)

    def delete(self, key: str) -> None:
        self._inner.delete(key)
