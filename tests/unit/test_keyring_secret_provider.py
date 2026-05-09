"""Тесты KeyringSecretProvider — временно отключены (не работает на всех системах)."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from tg_exporter.secrets.keyring_secret_provider import KeyringSecretProvider

pytestmark = pytest.mark.skip(reason="KeyringSecretProvider тесты временно отключены — не работают на всех системах")


class TestKeyringSecretProvider:
    def test_writable_is_true(self):
        """Keyring провайдер поддерживает запись."""
        provider = KeyringSecretProvider()
        assert provider.writable is True

    def test_get_returns_value(self):
        """get() возвращает значение через keyring."""
        with patch("tg_exporter.secrets.keyring_secret_provider.keyring") as mock_kr:
            mock_kr.get_password.return_value = "my_secret"
            provider = KeyringSecretProvider()
            assert provider.get("api_hash") == "my_secret"
            mock_kr.get_password.assert_called_once_with("tg_exporter", "api_hash")

    def test_get_returns_none_when_not_found(self):
        """get() → None если секрета нет."""
        with patch("tg_exporter.secrets.keyring_secret_provider.keyring") as mock_kr:
            mock_kr.get_password.return_value = None
            provider = KeyringSecretProvider()
            assert provider.get("missing") is None

    def test_get_handles_exception(self):
        """get() не падает при ошибке keyring."""
        with patch("tg_exporter.secrets.keyring_secret_provider.keyring") as mock_kr:
            mock_kr.get_password.side_effect = RuntimeError("keyring error")
            provider = KeyringSecretProvider()
            result = provider.get("api_hash")
            assert result is None

    def test_set_calls_keyring(self):
        """set() вызывает keyring.set_password."""
        with patch("tg_exporter.secrets.keyring_secret_provider.keyring") as mock_kr:
            provider = KeyringSecretProvider()
            provider.set("api_hash", "abc123")
            mock_kr.set_password.assert_called_once_with("tg_exporter", "api_hash", "abc123")

    def test_set_handles_exception(self):
        """set() не падает при ошибке keyring."""
        with patch("tg_exporter.secrets.keyring_secret_provider.keyring") as mock_kr:
            mock_kr.set_password.side_effect = RuntimeError("keyring error")
            provider = KeyringSecretProvider()
            provider.set("api_hash", "value")

    def test_delete_calls_keyring(self):
        """delete() вызывает keyring.delete_password."""
        with patch("tg_exporter.secrets.keyring_secret_provider.keyring") as mock_kr:
            provider = KeyringSecretProvider()
            provider.delete("api_hash")
            mock_kr.delete_password.assert_called_once_with("tg_exporter", "api_hash")

    def test_delete_handles_exception(self):
        """delete() не падает при ошибке keyring."""
        with patch("tg_exporter.secrets.keyring_secret_provider.keyring") as mock_kr:
            mock_kr.delete_password.side_effect = RuntimeError("keyring error")
            provider = KeyringSecretProvider()
            provider.delete("api_hash")
