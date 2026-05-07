from pathlib import Path
from typing import Optional

from tg_exporter_cli.secrets.secret_provider import SecretProvider


class EnvFileSecretProvider(SecretProvider):
    """Провайдер секретов из .env файла (только чтение)."""

    writable = False

    def __init__(self, env_path: Path) -> None:
        self._env_path = Path(env_path)
        self._values: dict[str, Optional[str]] = {}
        self._load()

    def _load(self) -> None:
        try:
            from dotenv import dotenv_values
            self._values = dotenv_values(self._env_path)
        except ImportError:
            self._values = {}

    def get(self, key: str) -> Optional[str]:
        return self._values.get(key)

    def set(self, key: str, value: str) -> None:
        raise NotImplementedError(
            "EnvFileSecretProvider is read-only (writable=False)"
        )

    def delete(self, key: str) -> None:
        # no-op: провайдер не пишет в .env
        pass
