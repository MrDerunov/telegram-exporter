"""ISettingsStore — интерфейс хранилища состояния приложения."""
from __future__ import annotations

from abc import ABC, abstractmethod

from tg_exporter.hosting.state_model import StateModel


class ISettingsStore(ABC):
    """Хранилище состояния приложения (профили, чаты, активный телефон).
    Реализация: JsonSettingsStore → state.json.
    """

    @abstractmethod
    def load(self) -> StateModel:
        """Загрузить состояние. Возвращает дефолтный StateModel если нет данных."""
        ...

    @abstractmethod
    def save(self, state: StateModel) -> None:
        """Сохранить состояние. Атомарная запись + безопасные права."""
        ...
