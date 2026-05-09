"""CliHost — хост CLI-приложения. Владеет DI-контейнером и управляет жизненным циклом."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Callable

from .container import Container
from tg_exporter_cli.hosting.cli_config import CliConfig, DEFAULT_CONFIG_DIR
from tg_exporter_cli.hosting.cli_config_repository import load_cli_config
from tg_exporter.secrets import SecretProvider, EnvVarsSecretProvider, EnvFileSecretProvider, ChainSecretProvider
from tg_exporter.hosting.app_config import AppConfig
from tg_exporter.telegram.credentials_manager import CredentialsManager
from tg_exporter.telegram.profiles.profile_manager import ProfileManager
from tg_exporter.telegram.telegram_client_manager import TelethonClientManager
from tg_exporter.telegram.telegram_client_manager_interface import ITelegramClientManager
from tg_exporter.telegram.auth.auth_service import AuthService
from tg_exporter.services.export_history import ExportHistory
from tg_exporter.services.export.export_orchestrator import ExportOrchestrator


class CliHost:
    """Хост CLI-приложения. Содержит DI-контейнер и управляет регистрацией сервисов."""

    def __init__(self, config_path: Path | None = None, env_file: Path | None = None) -> None:
        self._container = Container()
        self._config_path = config_path or DEFAULT_CONFIG_DIR / "cli_config.yaml"
        self._env_file = env_file or Path(".env")

    def build(self) -> CliHost:
        """Зарегистрировать все сервисы в контейнере."""
        c = self._container

        # 1. Секреты (порядок: env vars → .env file)
        c.register_instance(
            SecretProvider,
            ChainSecretProvider([
                EnvVarsSecretProvider(),
                EnvFileSecretProvider(self._env_file),
            ]),
        )

        # 2. Конфиг (публичные настройки, без секретов)
        c.register(CliConfig, lambda _: load_cli_config(self._config_path))

        # 3. AppConfig (адаптация CliConfig для core-слоя)
        def _create_app_config(ctr: Container) -> AppConfig:
            ac = AppConfig()
            cli_cfg = ctr.get(CliConfig)
            if cli_cfg.api_id:
                ac.api_id = cli_cfg.api_id
            return ac

        c.register(AppConfig, _create_app_config)

        # 4. CredentialsManager
        c.register(CredentialsManager, lambda _: CredentialsManager())

        # 5. Профили
        c.register(ProfileManager, lambda ctr: ProfileManager(ctr.get(CredentialsManager)))

        # 6. Telegram-клиент + интерфейс
        c.register(
            TelethonClientManager,
            lambda ctr: TelethonClientManager(ctr.get(AppConfig), ctr.get(CredentialsManager)),
        )
        c.register_interface(ITelegramClientManager, TelethonClientManager)

        # 7. Auth
        c.register(AuthService, lambda ctr: AuthService(ctr.get(ITelegramClientManager)))

        # 8. ExportHistory
        c.register(ExportHistory, lambda _: ExportHistory())

        # 9. Экспорт
        c.register(
            ExportOrchestrator,
            lambda ctr: ExportOrchestrator(
                ctr.get(ITelegramClientManager),
                ctr.get(AppConfig),
                ctr.get(ExportHistory),
            ),
        )

        return self

    def rebind_services(self, callback: Callable[[Container], None]) -> CliHost:
        """Позволяет переопределить регистрации сервисов (для тестов)."""
        callback(self._container)
        return self

    def run(self) -> None:
        """Запустить хост (заглушка, будет использоваться позже)."""
        pass

    def get(self, service_type: type) -> Any:
        """Получить сервис по типу."""
        return self._container.get(service_type)
