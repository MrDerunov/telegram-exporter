import os
from typing import Optional

from tg_exporter_cli.secrets.provider import SecretProvider

_PREFIX = "TG_EXPORTER_"


class EnvVarsSecretProvider(SecretProvider):
    """Провайдер секретов через переменные окружения (os.environ)."""

    writable = True

    def _full_key(self, key: str) -> str:
        return f"{_PREFIX}{key}"

    def get(self, key: str) -> Optional[str]:
        return os.environ.get(self._full_key(key))

    def set(self, key: str, value: str) -> None:
        os.environ[self._full_key(key)] = value

    def delete(self, key: str) -> None:
        os.environ.pop(self._full_key(key), None)
