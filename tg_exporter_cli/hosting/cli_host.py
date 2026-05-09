"""CliHost — хост CLI-приложения. Владеет DI-контейнером и управляет жизненным циклом."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Callable

import yaml

from .container import Container
from tg_exporter_cli.cli_constants import CONFIG_DIR, CONFIG_FILENAME, DEFAULT_ENV_FILENAME
from tg_exporter_cli.hosting.cli_config import CliConfig
from tg_exporter_cli.hosting.config_mapper import map_to_app_config
from tg_exporter.secrets import SecretProvider, EnvVarsSecretProvider, EnvFileSecretProvider, ChainSecretProvider
from tg_exporter.secrets.secret_keys import API_HASH, DEEPGRAM_API_KEY, SESSION
from tg_exporter.hosting.app_config import AppConfig
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
        self._config_path = config_path or CONFIG_DIR / CONFIG_FILENAME
        self._env_file = env_file or Path(DEFAULT_ENV_FILENAME)
        self._secret_provider: SecretProvider | None = None
        self._raw_config: dict = {}

    def build(self) -> CliHost:
        """Собрать конфигурацию и зарегистрировать все сервисы в контейнере."""
        self._raw_config = self._configure_cli()
        self._bind_services(self._raw_config)
        return self

    def _configure_cli(self) -> dict:
        """Читает конфигурацию и секреты, возвращает единый словарь."""
        # Цепочка секретов: env vars → .env file
        self._secret_provider = ChainSecretProvider([
            EnvVarsSecretProvider(),
            EnvFileSecretProvider(self._env_file),
        ])

        # Сырой YAML → dict
        if self._config_path.exists():
            with open(self._config_path, "r") as f:
                yaml_data = yaml.safe_load(f) or {}
        else:
            yaml_data = {}

        # Мёрж секретов в YAML-словарь
        yaml_data["api_hash"] = self._secret_provider.get(API_HASH) or ""
        yaml_data["deepgram_api_key"] = self._secret_provider.get(DEEPGRAM_API_KEY) or ""
        yaml_data["session"] = self._secret_provider.get(SESSION) or ""

        return yaml_data

    def _bind_services(self, raw_config: dict) -> None:
        """Маппит сырой конфиг на типизированные объекты и регистрирует сервисы."""
        container = self._container

        # SecretProvider
        container.register_instance(SecretProvider, self._secret_provider)

        # CliConfig (frozen) — из словаря
        cli_config = CliConfig.from_raw(raw_config)
        container.register_instance(CliConfig, cli_config)

        # AppConfig (frozen) — через mapper
        app_config = map_to_app_config(cli_config)
        container.register_instance(AppConfig, app_config)

        # Профили
        container.register(
            ProfileManager,
            lambda ctr: ProfileManager(ctr.get(SecretProvider)),
        )

        # Telegram-клиент + интерфейс
        container.register(
            ITelegramClientManager,
            lambda ctr: TelethonClientManager(
                ctr.get(AppConfig),
                ctr.get(SecretProvider),
            ),
        )

        # Auth
        container.register(
            AuthService,
            lambda ctr: AuthService(ctr.get(ITelegramClientManager)),
        )

        # ExportHistory
        container.register(ExportHistory, lambda _: ExportHistory())

        # Экспорт
        container.register(
            ExportOrchestrator,
            lambda ctr: ExportOrchestrator(
                ctr.get(ITelegramClientManager),
                ctr.get(AppConfig),
                ctr.get(ExportHistory),
            ),
        )

    def rebind_services(self, callback: Callable[[Container, dict], None]) -> CliHost:
        """Позволяет переопределить регистрации сервисов (для тестов).
        callback получает (container, raw_config)."""
        callback(self._container, self._raw_config)
        return self

    def run(self) -> None:
        """Запустить хост (заглушка, будет использоваться позже)."""
        pass

    def get(self, service_type: type) -> Any:
        """Получить сервис по типу."""
        return self._container.get(service_type)

    @property
    def config_path(self) -> Path:
        """Путь к файлу конфига."""
        return self._config_path
