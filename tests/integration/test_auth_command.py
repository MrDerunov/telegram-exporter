"""Интеграционные тесты CLI-команд auth."""

from __future__ import annotations

from tg_exporter.settings.secrets.secret_store import ISecretStore
from tg_exporter.settings.secrets import SESSION, API_HASH
from tests.integration.test_cli_command_base import TestCliCommandBase


# ---------------------------------------------------------------------------
# auth login
# ---------------------------------------------------------------------------

class TestAuthLogin(TestCliCommandBase):
    """Флоу авторизации: send_code → verify_code → save_session."""

    def test_full_login_flow(self):
        """Успешный вход: отправка кода, ввод кода, авторизация."""
        self.server.auth.set_authorized(False)

        result = self._invoke("auth", "login", "--phone", "+7999",
                              "--api-id", "42", "--api-hash", "abc",
                              input="12345\n")

        assert result.exit_code == 0
        assert self.server.auth.is_authorized()
        assert "send_code_request(+7999)" in self.client.call_log
        assert any("sign_in" in entry for entry in self.client.call_log)


# ---------------------------------------------------------------------------
# auth status
# ---------------------------------------------------------------------------

class TestAuthStatus(TestCliCommandBase):
    """Проверка статуса авторизации."""

    def test_exit_0_when_authorized(self):
        self.server.auth.set_authorized(True)
        result = self._invoke("auth", "status")
        assert result.exit_code == 0

    def test_exit_0_when_not_authorized(self):
        self.server.auth.set_authorized(False)
        result = self._invoke("auth", "status")
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# auth verify
# ---------------------------------------------------------------------------

class TestAuthVerify(TestCliCommandBase):
    """Проверка сессии для CI/CD."""

    def test_exit_0_when_session_valid(self):
        self.server.auth.set_authorized(True)
        result = self._invoke("auth", "verify")
        assert result.exit_code == 0

    def test_exit_1_when_session_invalid(self):
        self.server.auth.set_authorized(False)
        result = self._invoke("auth", "verify")
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# auth logout
# ---------------------------------------------------------------------------

class TestAuthLogout(TestCliCommandBase):
    """Выход из аккаунта."""

    def test_clears_auth_state(self):
        result = self._invoke("auth", "logout")

        assert result.exit_code == 0
        assert "log_out" in self.client.call_log
        assert not self.server.auth.is_authorized()

    def test_exit_0_when_not_authorized(self):
        self.server.auth.set_authorized(False)
        result = self._invoke("auth", "logout")
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# auth export-session
# ---------------------------------------------------------------------------

class TestAuthExportSession(TestCliCommandBase):
    """Экспорт сессии в .env файл."""

    def test_creates_env_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TG_EXPORTER_API_ID", "42")
        secret_store = self.host.get(ISecretStore)
        secret_store.set(SESSION, "test_session_string")
        secret_store.set(API_HASH, "test_hash")
        output = tmp_path / "secrets.env"

        result = self._invoke("auth", "export-session", "--output", str(output))

        assert result.exit_code == 0
        assert output.exists()
        content = output.read_text()
        assert "TG_EXPORTER_SESSION=test_session_string" in content
        assert "TG_EXPORTER_API_HASH=test_hash" in content

    def test_fails_when_no_session(self):
        secret_store = self.host.get(ISecretStore)
        secret_store.delete(SESSION)

        result = self._invoke("auth", "export-session")

        assert result.exit_code != 0
