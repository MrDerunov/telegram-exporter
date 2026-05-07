from abc import ABC, abstractmethod
from typing import Optional


class SecretProvider(ABC):
    """Абстракция над источником секретов (api_hash, session, токены).

    Каждый провайдер указывает, может ли он сохранять секреты через поле writable.
    ChainSecretProvider при set() пишет только в writable провайдеры.
    """

    writable: bool = False

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Прочитать секрет. Возвращает None если не найден."""
        ...

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Сохранить секрет. Кидает исключение если не поддерживается."""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Удалить секрет. Не кидает исключение если не найден."""
        ...
