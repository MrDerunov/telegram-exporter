"""CliHost — хост CLI-приложения. Владеет DI-контейнером и управляет жизненным циклом."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Callable

from .container import Container
from tg_exporter_cli.cli_constants import CONFIG_DIR, CONFIG_FILENAME, DEFAULT_ENV_FILENAME
from tg_exporter_cli.hosting.cli_config import CliConfig
from tg_exporter_cli.hosting.cli_config_repository import load_cli_config
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

        # YAML-конфиг → CliConfig → словарь (без секретов)
        cli_config = load_cli_config(self._config_path)

        # Чтение секретов из SecretProvider
        api_hash = self._secret_provider.get(API_HASH) or ""
        deepgram_api_key = self._secret_provider.get(DEEPGRAM_API_KEY) or ""
        session = self._secret_provider.get(SESSION) or ""

        # Мёрж: YAML-поля + секреты
        return {
            "version": cli_config.version,
            "api_id": cli_config.api_id,
            "api_hash": api_hash,
            "default_profile": cli_config.default_profile,
            "chats": cli_config.chats,
            "default_format": cli_config.default_format,
            "default_words_per_file": cli_config.default_words_per_file,
            "default_download_media": cli_config.default_download_media,
            "default_transcribe": cli_config.default_transcribe,
            "default_analytics": cli_config.default_analytics,
            "transcription_provider": cli_config.transcription_provider,
            "transcription_model": cli_config.transcription_model,
            "transcription_language": cli_config.transcription_language,
            "deepgram_api_key": deepgram_api_key,
            "secrets_source": cli_config.secrets_source,
            "log_level": cli_config.log_level,
            "log_file": cli_config.log_file,
            "retry_max_attempts": cli_config.retry_max_attempts,
            "retry_delay_seconds": cli_config.retry_delay_seconds,
            "retry_max_delay_seconds": cli_config.retry_max_delay_seconds,
            "rate_limit_media_download_delay_ms": cli_config.rate_limit_media_download_delay_ms,
            "rate_limit_message_fetch_delay_ms": cli_config.rate_limit_message_fetch_delay_ms,
            "session": session,
        }

    def _bind_services(self, raw_config: dict) -> None:
        """Маппит сырой конфиг на типизированные объекты и регистрирует сервисы."""
        c = self._container

        # SecretProvider
        c.register_instance(SecretProvider, self._secret_provider)

        # CliConfig (frozen) — из словаря
        cli_config = CliConfig.from_raw(raw_config)
        c.register_instance(CliConfig, cli_config)

        # AppConfig (frozen) — через mapper
        app_config = map_to_app_config(cli_config)
        c.register_instance(AppConfig, app_config)

        # Профили
        c.register(
            ProfileManager,
            lambda ctr: ProfileManager(ctr.get(SecretProvider)),
        )

        # Telegram-клиент + интерфейс
        c.register(
            TelethonClientManager,
            lambda ctr: TelethonClientManager(
                ctr.get(AppConfig),
                ctr.get(SecretProvider),
            ),
        )
        c.register_interface(ITelegramClientManager, TelethonClientManager)

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
