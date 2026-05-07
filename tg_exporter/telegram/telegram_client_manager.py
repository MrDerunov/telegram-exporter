"""TelethonClientManager — фабрика, создающая TelethonClientAdapter.
Читает credentials из CredentialsManager, создаёт адаптер с нужной сессией.
"""
from __future__ import annotations
import threading
from typing import Optional

from .telegram_client_manager_interface import ITelegramClientManager
from .telegram_client_interface import TelegramClientInterface
from .telethon_client_adapter import TelethonClientAdapter
from .credentials_manager import CredentialsManager
from tg_exporter.hosting.app_config import AppConfig


class ClientNotConfiguredError(RuntimeError):
    """api_id или api_hash не заданы."""


class TelethonClientManager(ITelegramClientManager):
    """Создаёт TelethonClientAdapter с правильной сессией и конфигом."""

    def __init__(self, config: AppConfig, credentials: CredentialsManager) -> None:
        self._config = config
        self._credentials = credentials
        self._session_override: Optional[str] = None
        self._current_client: Optional[TelethonClientAdapter] = None
        self._lock = threading.Lock()

    def update_config(self, config: AppConfig) -> None:
        """Обновляет конфиг. Если api_id изменился — сбрасывает клиент."""
        with self._lock:
            if self._config.api_id != config.api_id:
                if self._current_client is not None:
                    self._current_client.destroy()
                    self._current_client = None
            self._config = config

    def use_session(self, session_string: Optional[str]) -> None:
        """Указать конкретную сессию (для профилей)."""
        with self._lock:
            self._session_override = session_string
            if self._current_client is not None:
                self._current_client.destroy()
                self._current_client = None

    def create_client(self) -> TelegramClientInterface:
        """Создать и вернуть TelethonClientAdapter."""
        with self._lock:
            if self._current_client is not None:
                return self._current_client

            api_id = self._config.api_id_int
            if not api_id:
                raise ClientNotConfiguredError(
                    "api_id не задан. Настройте конфиг."
                )

            api_hash = self._credentials.load_api_hash(self._config.api_id)
            if not api_hash:
                raise ClientNotConfiguredError(
                    "api_hash не найден. Введите API Hash."
                )

            session_str = (
                self._session_override
                or self._credentials.load_session(self._config.api_id)
                or ""
            )

            self._current_client = TelethonClientAdapter(
                api_id=api_id,
                api_hash=api_hash,
                session_str=session_str,
            )
            return self._current_client

    def save_session(self) -> None:
        """Сохранить сессию в CredentialsManager."""
        with self._lock:
            if self._current_client is None:
                return
            try:
                session_str = self._current_client.save_session()
                if session_str and self._config.api_id:
                    self._credentials.save_session(self._config.api_id, session_str)
            except Exception:
                pass

    def destroy(self) -> None:
        """Уничтожить клиент."""
        with self._lock:
            if self._current_client is not None:
                self._current_client.destroy()
                self._current_client = None
