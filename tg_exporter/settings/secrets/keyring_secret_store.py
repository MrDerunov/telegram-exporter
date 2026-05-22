"""KeyringSecretStore — хранилище секретов через системный keyring."""
from __future__ import annotations

import logging

from tg_exporter.settings.secrets.secret_store import ISecretStore

logger = logging.getLogger(__name__)

_SERVICE = "tg-exporter"


class KeyringSecretStore(ISecretStore):
    """Провайдер секретов через системный keyring."""

    def get(self, key: str) -> str | None:
        try:
            import keyring
            return keyring.get_password(_SERVICE, key)
        except Exception:
            logger.warning("Failed to read secret %r from keyring", key, exc_info=True)
            return None

    def set(self, key: str, value: str) -> None:
        try:
            import keyring
            keyring.set_password(_SERVICE, key, value)
        except Exception:
            logger.warning("Failed to write secret %r to keyring", key, exc_info=True)

    def delete(self, key: str) -> None:
        try:
            import keyring
            keyring.delete_password(_SERVICE, key)
        except Exception:
            logger.warning("Failed to delete secret %r from keyring", key, exc_info=True)
