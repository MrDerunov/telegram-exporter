"""Container — DI-контейнер CLI-приложения.
Собирает все зависимости в одном месте.
Через параметр telegram_client можно подменить менеджер для тестов.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

from tg_exporter.telegram.telegram_client_manager_interface import ITelegramClientManager
from tg_exporter.telegram.telegram_client_manager import TelethonClientManager
from tg_exporter.telegram.credentials_manager import CredentialsManager
from tg_exporter.telegram.auth.auth_service import AuthService
from tg_exporter.services.export.export_orchestrator import ExportOrchestrator
from tg_exporter.telegram.profiles.profile_manager import ProfileManager
from tg_exporter.hosting.app_config import AppConfig
from tg_exporter.services.export_history import ExportHistory

from tg_exporter.secrets import ChainSecretProvider, EnvVarsSecretProvider, EnvFileSecretProvider
from .cli_config import CliConfig, DEFAULT_CONFIG_DIR


class Container:
    """Собирает и предоставляет все зависимости CLI-приложения."""

    def __init__(
        self,
        config_path: Path | None = None,
        env_file: Path | None = None,
        telegram_manager: ITelegramClientManager | None = None,
    ):
        config_path = config_path or DEFAULT_CONFIG_DIR / "cli_config.yaml"
        env_file = env_file or Path(".env")

        # 1. Секреты (порядок: env vars → .env file)
        # keyring_provider не подключаем по умолчанию — на headless-системах недоступен
        self.secret_provider = ChainSecretProvider([
            EnvVarsSecretProvider(),
            EnvFileSecretProvider(env_file),
        ])

        # 2. Конфиг (публичные настройки, без секретов)
        self.config = CliConfig.load(config_path)

        # 3. AppConfig (адаптация CliConfig для core-слоя)
        self.app_config = AppConfig()
        if self.config.api_id:
            self.app_config.api_id = self.config.api_id

        # 4. Credentials (api_hash, session — пока через старый CredentialsManager)
        self.credentials = CredentialsManager()

        # 5. Профили
        self.profile_manager = ProfileManager(self.credentials)

        # 6. Telegram-клиент (реальный или фейковый для тестов)
        if telegram_manager is not None:
            self.client_manager = telegram_manager
        else:
            self.client_manager = TelethonClientManager(self.app_config, self.credentials)

        # 7. Auth
        self.auth_service = AuthService(self.client_manager)

        # 8. Экспорт (ленивая инициализация)
        self._orchestrator: ExportOrchestrator | None = None

    @property
    def orchestrator(self) -> ExportOrchestrator:
        if self._orchestrator is None:
            export_history = ExportHistory()
            self._orchestrator = ExportOrchestrator(
                self.client_manager, self.app_config, export_history
            )
        return self._orchestrator
