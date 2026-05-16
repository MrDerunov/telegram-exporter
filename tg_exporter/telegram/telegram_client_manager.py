"""TelethonClientManager — фабрика, создающая TelethonClientAdapter.
Читает api_hash из StaticConfig, сессию из ISecretStore.
"""
from __future__ import annotations
import threading
from typing import Optional

from .telegram_client_manager_interface import ITelegramClientManager
from .telegram_client_interface import TelegramClientInterface
from .telethon_client_adapter import TelethonClientAdapter
from tg_exporter.secrets.secret_store import ISecretStore
from tg_exporter.secrets.secret_keys import SESSION, API_HASH, API_ID
from tg_exporter.hosting.static_config import StaticConfig


class ClientNotConfiguredError(RuntimeError):
    """api_id или api_hash не заданы."""


class TelethonClientManager(ITelegramClientManager):
    """Создаёт TelethonClientAdapter с правильной сессией и конфигом."""

    def __init__(self, config: StaticConfig, secrets: ISecretStore) -> None:
        self._config = config
        self._secrets = secrets
        self._session_override: Optional[str] = None
        self._current_client: Optional[TelethonClientAdapter] = None
        self._lock = threading.Lock()

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

            # api_id: сначала из конфига, затем из секретов (как для api_hash)
            api_id_str = self._config.api_id or self._secrets.get(API_ID) or ""
            digits = "".join(c for c in api_id_str if c.isdigit())
            api_id = int(digits) if digits else None
            if not api_id:
                raise ClientNotConfiguredError(
                    "api_id не задан. Настройте конфиг."
                )

            api_hash = self._config.api_hash or self._secrets.get(API_HASH) or ""
            if not api_hash:
                raise ClientNotConfiguredError(
                    "api_hash не найден. Введите API Hash."
                )

            session_str = (
                self._session_override
                or self._secrets.get(SESSION)
                or ""
            )

            self._current_client = TelethonClientAdapter(
                api_id=api_id,
                api_hash=api_hash,
                session_str=session_str,
            )
            return self._current_client

    def save_session(self) -> None:
        """Сохранить сессию в SecretProvider."""
        with self._lock:
            if self._current_client is None:
                return
            try:
                session_str = self._current_client.save_session()
                if session_str:
                    self._secrets.set(SESSION, session_str)
            except Exception:
                pass

    def destroy(self) -> None:
        """Уничтожить клиент."""
        with self._lock:
            if self._current_client is not None:
                self._current_client.destroy()
                self._current_client = None
