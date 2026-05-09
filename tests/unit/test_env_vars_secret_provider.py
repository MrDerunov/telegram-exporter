"""Тесты EnvVarsSecretProvider."""
from __future__ import annotations

import os

from tg_exporter.secrets.env_vars_secret_provider import EnvVarsSecretProvider


class TestEnvVarsSecretProvider:
    def test_get_set_delete(self):
        """Чтение, запись, удаление переменной."""
        provider = EnvVarsSecretProvider()
        provider.set("TEST_VAR", "test_value")
        assert provider.get("TEST_VAR") == "test_value"
        provider.delete("TEST_VAR")
        assert provider.get("TEST_VAR") is None

    def test_prefix_added(self):
        """Ключ автоматически получает префикс TG_EXPORTER_."""
        provider = EnvVarsSecretProvider()
        provider.set("MY_KEY", "secret")
        assert os.environ.get("TG_EXPORTER_MY_KEY") == "secret"
        provider.delete("MY_KEY")

    def test_get_missing_returns_none(self):
        """Отсутствующая переменная → None."""
        provider = EnvVarsSecretProvider()
        result = provider.get("NONEXISTENT_KEY_99999")
        assert result is None

    def test_delete_missing_does_not_crash(self):
        """delete() несуществующей переменной не падает."""
        provider = EnvVarsSecretProvider()
        provider.delete("DOES_NOT_EXIST_99999")

    def test_writable_is_true(self):
        """EnvVars провайдер — writable."""
        provider = EnvVarsSecretProvider()
        assert provider.writable is True

    def test_overwrite_existing(self):
        """Перезапись существующей переменной."""
        provider = EnvVarsSecretProvider()
        provider.set("OVERWRITE_TEST", "v1")
        provider.set("OVERWRITE_TEST", "v2")
        assert provider.get("OVERWRITE_TEST") == "v2"
        provider.delete("OVERWRITE_TEST")
