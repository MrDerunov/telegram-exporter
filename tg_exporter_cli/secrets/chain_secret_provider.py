from typing import Optional

from tg_exporter_cli.secrets.secret_provider import SecretProvider


class ChainSecretProvider(SecretProvider):
    """Объединяет несколько провайдеров в цепочку.

    При чтении — первый не-None результат (env_vars перезаписывает env_file).
    При записи — пишет только в провайдеры с writable=True.
    """

    writable = True  # цепочка считается writable если есть хотя бы один writable провайдер

    def __init__(self, providers: list[SecretProvider]) -> None:
        self._providers = providers

    def get(self, key: str) -> Optional[str]:
        for p in self._providers:
            value = p.get(key)
            if value is not None:
                return value
        return None

    def set(self, key: str, value: str) -> None:
        for p in self._providers:
            if p.writable:
                p.set(key, value)

    def delete(self, key: str) -> None:
        for p in self._providers:
            if p.writable:
                p.delete(key)
