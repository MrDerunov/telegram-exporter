"""Container — универсальный DI-контейнер.
Все сервисы регистрируются как singleton: создаются при первом запросе через get(),
кешируются и возвращаются при последующих запросах.
"""
from __future__ import annotations
from typing import Any
from collections.abc import Callable


class Container:
    """Универсальный DI-контейнер с поддержкой singleton-сервисов."""

    def __init__(self) -> None:
        self._factories: dict[type, Callable[[Container], Any]] = {}
        self._instances: dict[type, Any] = {}
        self._interface_map: dict[type, type] = {}

    def register(self, service_type: type, factory: Callable[[Container], Any]) -> None:
        """Зарегистрировать сервис с фабрикой. Инстанс создаётся лениво при первом get()."""
        self._factories[service_type] = factory

    def register_instance(self, service_type: type, instance: Any) -> None:
        """Зарегистрировать готовый инстанс сервиса."""
        self._instances[service_type] = instance

    def register_interface(self, interface_type: type, implementation_type: type) -> None:
        """Связать интерфейс с его реализацией. get() будет работать по обоим типам."""
        self._interface_map[interface_type] = implementation_type

    def get(self, service_type: type) -> Any:
        """Получить инстанс сервиса. Создаёт singleton при первом обращении."""
        if service_type in self._instances:
            return self._instances[service_type]

        actual_type = self._interface_map.get(service_type, service_type)

        if actual_type not in self._instances:
            factory = self._factories[actual_type]
            self._instances[actual_type] = factory(self)

        return self._instances[actual_type]
