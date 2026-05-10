"""ISecretStore — интерфейс хранилища секретов (api_hash, ключи, сессии)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class ISecretStore(ABC):
    """Хранилище секретов. Реализации:
    - KeyringSecretStore — системный keyring (по умолчанию, для ручного использования)
    - JsonSecretStore — secrets.json (для CI)
    """

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Прочитать секрет. Возвращает None если не найден."""
        ...

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Сохранить секрет."""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Удалить секрет. Не кидает исключение если не найден."""
        ...
