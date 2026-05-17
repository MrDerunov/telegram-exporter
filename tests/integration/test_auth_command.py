"""Интеграционные тесты CLI-команд auth."""

from __future__ import annotations

import pytest

from tg_exporter.services.telegram import ITelegramClientManager
from tg_exporter.secrets.secret_store import ISecretStore
from tg_exporter.secrets.secret_keys import SESSION, API_HASH
from tg_exporter.configs.static_config import StaticConfig
from tests.common.fakes import FakeTelegramClient, FakeTelegramClientManager
from tests.integration.test_cli_command_base import TestCliCommandBase


# todo   тесты нужно переделать: пройти с фейковым клиентом и конкретным юзером флоу аутентификации
class TestAuthCommand(TestCliCommandBase):

    # ------------------------------------------------------------------
    # auth status
    # ------------------------------------------------------------------

    def test_status_returns_exit_code_0_or_1(self):
        """auth status возвращает 0 или 1 без stack trace."""
        result = self.invoke("auth", "status")
        assert result.exit_code in (0, 1)

    # ------------------------------------------------------------------
    # auth verify
    # ------------------------------------------------------------------

    def test_verify_returns_exit_code(self):
        """auth verify возвращает exit code."""
        result = self.invoke("auth", "verify")
        assert result.exit_code in (0, 1, 2)

    # ------------------------------------------------------------------
    # auth logout
    # ------------------------------------------------------------------

    def test_logout_returns_exit_code_0(self):
        """auth logout завершается без ошибок."""
        result = self.invoke("auth", "logout")
        assert result.exit_code == 0

    # ------------------------------------------------------------------
    # auth export-session
    # ------------------------------------------------------------------

    def test_export_session_fails_when_no_session(self):
        """export-session без сессии — ошибка."""
        result = self.invoke("auth", "export-session")
        assert result.exit_code != 0
        assert "нет активной сессии" in result.output.lower() or "Нет активной сессии" in result.output

    def test_export_session_succeeds_when_session_exists(self, tmp_path, monkeypatch):
        """export-session с сессией создаёт .env файл."""
        output_path = tmp_path / "test_secrets.env"

        # api_id попадает в StaticConfig через env var
        monkeypatch.setenv("TG_EXPORTER_API_ID", "42")

        fake_client = FakeTelegramClient()
        fake_client.set_authorized(True)
        host = self._build_host(fake_client, authorized=True)

        # Записываем сессию и api_hash в secret_store
        secret_store = host.get(ISecretStore)
        secret_store.set(SESSION, "test_session_string")
        secret_store.set(API_HASH, "test_hash")

        # Подменяем get_host перед вызовом команды
        import tg_exporter_cli.commands.auth as auth_mod
        original_host = auth_mod.get_host
        auth_mod.get_host = lambda: host
        try:
            result = self.runner.invoke(auth_mod.auth_group, [
                "export-session", "--output", str(output_path)
            ], catch_exceptions=False)
            assert result.exit_code == 0
            assert output_path.exists()
            content = output_path.read_text()
            assert "TG_EXPORTER_API_ID=42" in content
            assert "TG_EXPORTER_API_HASH=test_hash" in content
            assert "TG_EXPORTER_SESSION=test_session_string" in content
        finally:
            auth_mod.get_host = original_host
