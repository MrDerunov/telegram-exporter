"""CliHost — хост CLI-приложения. Владеет DI-контейнером и управляет жизненным циклом."""
from __future__ import annotations
from typing import Any, Callable

from .container import Container
from tg_exporter.hosting.configuration_provider import (
    ConfigurationProvider,
    ConfigurationResult,
    resolve_config_dir,
)
from tg_exporter.hosting.static_config import StaticConfig
from tg_exporter.hosting.state_model import StateModel
from tg_exporter.hosting.settings_store import ISettingsStore
from tg_exporter.hosting.json_settings_store import JsonSettingsStore
from tg_exporter.secrets.secret_store import ISecretStore
from tg_exporter.secrets.keyring_secret_store import KeyringSecretStore
from tg_exporter.secrets.json_secret_store import JsonSecretStore
from tg_exporter.telegram.profiles.profile_manager import ProfileManager
from tg_exporter.telegram.telegram_client_manager import TelethonClientManager
from tg_exporter.telegram.telegram_client_manager_interface import ITelegramClientManager
from tg_exporter.telegram.auth.auth_service import AuthService
from tg_exporter.services.export_history import ExportHistory
from tg_exporter.services.export.export_orchestrator import ExportOrchestrator


class CliHost:
    """Хост CLI-приложения. Содержит DI-контейнер и управляет регистрацией сервисов."""

    def __init__(self) -> None:
        self._container = Container()

    def build(self) -> CliHost:
        """Собрать конфигурацию и зарегистрировать все сервисы в контейнере.
        Только чтение конфигов и DI-регистрация — без создания файлов/папок."""
        config_dir = resolve_config_dir()
        provider = ConfigurationProvider(config_dir)
        result = provider.build()
        self._bind_services(result)
        return self

    def _bind_services(self, result: ConfigurationResult) -> None:
        """Маппит сырой конфиг на типизированные объекты и регистрирует сервисы."""
        c = self._container

        # ConfigurationResult — для доступа к config_dir и сырым данным
        c.register_instance(ConfigurationResult, result)

        # Маппинг сырого словаря в типизированные конфиги (делает хост)
        static_config = StaticConfig.from_raw(result.raw)
        state_model = StateModel.from_dict(result.raw)

        c.register_instance(StaticConfig, static_config)
        c.register_instance(StateModel, state_model)

        # SecretStore — тип выбирается на основе настройки из static_config
        if static_config.secrets_source == "file":
            secret_store: ISecretStore = JsonSecretStore(result.config_dir)
        else:
            secret_store = KeyringSecretStore()
        c.register_instance(ISecretStore, secret_store)

        # SettingsStore
        settings_store = JsonSettingsStore(result.config_dir)
        c.register_instance(ISettingsStore, settings_store)

        # Профили
        c.register(
            ProfileManager,
            lambda ctr: ProfileManager(
                secrets=ctr.get(ISecretStore),
                settings=ctr.get(ISettingsStore),
            ),
        )

        # Telegram-клиент + интерфейс
        c.register(
            ITelegramClientManager,
            lambda ctr: TelethonClientManager(
                config=ctr.get(StaticConfig),
                secrets=ctr.get(ISecretStore),
            ),
        )

        # Auth
        c.register(
            AuthService,
            lambda ctr: AuthService(ctr.get(ITelegramClientManager)),
        )

        # ExportHistory
        c.register(ExportHistory, lambda _: ExportHistory())

        # Экспорт
        c.register(
            ExportOrchestrator,
            lambda ctr: ExportOrchestrator(
                ctr.get(ITelegramClientManager),
                ctr.get(StaticConfig),
                ctr.get(ExportHistory),
            ),
        )

    def rebind_services(self, callback: Callable[[Container, ConfigurationResult], None]) -> CliHost:
        """Позволяет переопределить регистрации сервисов (для тестов).
        callback получает (container, ConfigurationResult)."""
        result = self._container.get(ConfigurationResult)
        callback(self._container, result)
        return self

    def run(self) -> None:
        """Инициализация ОС-ресурсов: логгер, директории.
        Вызывается ПОСЛЕ build() при старте приложения."""
        result = self._container.get(ConfigurationResult)
        from tg_exporter.utils.logger import init_logger
        init_logger(result.config_dir)

    def get(self, service_type: type) -> Any:
        """Получить сервис по типу."""
        return self._container.get(service_type)
