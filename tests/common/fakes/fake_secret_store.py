"""In-memory ISecretStore для тестов."""
from __future__ import annotations
from tg_exporter.settings.secrets.secret_store import ISecretStore


class FakeSecretStore(ISecretStore):
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(self, key: str, value: str) -> None:
        self.store[key] = value

    def delete(self, key: str) -> None:
        self.store.pop(key, None)
