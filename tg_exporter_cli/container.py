"""Container — DI-контейнер CLI-приложения.
Собирает все зависимости в одном месте.
Через параметр telegram_client можно подменить клиент для тестов.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

from tg_exporter.core import TelegramClientInterface, TelethonClientAdapter
from tg_exporter.core.telegram_client_manager import TelegramClientManager
from tg_exporter.core.credentials_manager import CredentialsManager
from tg_exporter.core.auth.auth_service import AuthService
from tg_exporter.core.export_orchestrator import ExportOrchestrator
from tg_exporter.core.profiles.profile_manager import ProfileManager
from tg_exporter.models.app_config import AppConfig
from tg_exporter.services.export_history import ExportHistory

from .secrets import ChainSecretProvider, EnvVarsSecretProvider, EnvFileSecretProvider
from .cli_config import CliConfig, DEFAULT_CONFIG_DIR


class Container:
    """Собирает и предоставляет все зависимости CLI-приложения."""

    def __init__(
        self,
        config_path: Path | None = None,
        env_file: Path | None = None,
        telegram_client: TelegramClientInterface | None = None,
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
        self.profile_manager = ProfileManager(
            self.credentials, self.app_config
        )

        # 6. Telegram-клиент (реальный или фейковый для тестов)
        if telegram_client is not None:
            self.client = telegram_client
        else:
            self.client_manager = TelegramClientManager(self.app_config, self.credentials)
            self.client = TelethonClientAdapter(self.client_manager)

        # 7. Auth
        self.auth_service = AuthService(self.client)

        # 8. Экспорт (ленивая инициализация)
        self._orchestrator: ExportOrchestrator | None = None

    @property
    def orchestrator(self) -> ExportOrchestrator:
        if self._orchestrator is None:
            export_history = ExportHistory()
            self._orchestrator = ExportOrchestrator(
                self.client, self.app_config, export_history
            )
        return self._orchestrator
