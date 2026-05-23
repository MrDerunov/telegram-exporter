"""Интеграционные тесты взаимодействия auth-команд с профилями."""

from __future__ import annotations

from tg_exporter.settings.secrets import SESSION
from .test_cli_command_base import TestCliCommandBase


class TestAuthProfileInteraction(TestCliCommandBase):
    """Тесты совместной работы auth + profile команд."""

    # ------------------------------------------------------------------
    # auth login → создаёт профиль
    # ------------------------------------------------------------------

    def test_login_creates_default_profile(self):
        """После auth login создаётся профиль с именем Default."""
        self.server.auth.set_authorized(False)

        result = self._invoke("auth", "login", "--phone", "+79991112233",
                              "--api-id", "42", "--api-hash", "abc",
                              input="12345\n")

        assert result.exit_code == 0
        assert self.pm.get("+79991112233") is not None
        assert self.pm.active_phone() == "+79991112233"
        assert self.pm.get("+79991112233").display_name == "Default"

    def test_login_preserves_existing_profile_name(self):
        """Если профиль уже существует с именем, login не затирает имя."""
        self.pm.add_or_update("+79991112233", "42", "", display_name="Личный")
        self.server.auth.set_authorized(False)

        result = self._invoke("auth", "login", "--phone", "+79991112233",
                              "--api-id", "42", "--api-hash", "abc",
                              input="12345\n")

        assert result.exit_code == 0
        assert self.pm.get("+79991112233").display_name == "Личный"

    # ------------------------------------------------------------------
    # auth status → использует сессию активного профиля
    # ------------------------------------------------------------------

    def test_status_uses_active_profile_session(self):
        """auth status загружает сессию активного профиля."""
        self.pm.add_or_update("+79991112233", "42", "my-session-token")
        self.server.auth.set_authorized(True)

        result = self._invoke("auth", "status")

        assert result.exit_code == 0
        assert self.client_manager._use_session_calls[-1] == "my-session-token"

    def test_status_when_no_active_profile_still_works(self):
        """auth status работает даже без активного профиля (обратная совместимость)."""
        self.server.auth.set_authorized(True)

        result = self._invoke("auth", "status")

        assert result.exit_code == 0

    # ------------------------------------------------------------------
    # auth status после profile switch
    # ------------------------------------------------------------------

    def test_status_after_profile_switch_uses_new_session(self):
        """После переключения профиля auth status использует сессию нового профиля."""
        self.pm.add_or_update("+79991112233", "42", "session-A")
        self.pm.add_or_update("+79992223344", "42", "session-B", set_active=False)
        self.pm.set_active("+79992223344")
        self.server.auth.set_authorized(True)

        result = self._invoke("auth", "status")

        assert result.exit_code == 0
        assert self.client_manager._use_session_calls[-1] == "session-B"

    # ------------------------------------------------------------------
    # auth logout → очищает сессию профиля
    # ------------------------------------------------------------------

    def test_logout_clears_active_profile_session(self):
        """auth logout очищает сессию активного профиля."""
        self.pm.add_or_update("+79991112233", "42", "session-token")

        result = self._invoke("auth", "logout")

        assert result.exit_code == 0
        assert self.pm.load_session(self.pm.get("+79991112233")) in (None, "")
        assert not self.server.auth.is_authorized()

    def test_logout_when_no_active_profile_still_works(self):
        """auth logout работает даже без активного профиля (обратная совместимость)."""
        self.server.auth.set_authorized(True)

        result = self._invoke("auth", "logout")

        assert result.exit_code == 0
        assert not self.server.auth.is_authorized()

    # ------------------------------------------------------------------
    # auth verify → использует сессию активного профиля
    # ------------------------------------------------------------------

    def test_verify_uses_active_profile_session(self):
        """auth verify загружает сессию активного профиля."""
        self.pm.add_or_update("+79991112233", "42", "session-token")
        self.server.auth.set_authorized(True)

        result = self._invoke("auth", "verify")

        assert result.exit_code == 0
        assert self.client_manager._use_session_calls[-1] == "session-token"

    # ------------------------------------------------------------------
    # Полный цикл: login → status → switch → logout
    # ------------------------------------------------------------------

    def test_full_cycle_login_switch_logout(self):
        """Полный цикл: login → проверка профиля → switch → status → logout."""
        self.server.auth.set_authorized(False)

        # Login
        r = self._invoke("auth", "login", "--phone", "+79991112233",
                         "--api-id", "42", "--api-hash", "abc",
                         input="12345\n")
        assert r.exit_code == 0
        assert self.pm.active_phone() == "+79991112233"

        # Add second profile and switch
        self.pm.add_or_update("+79992223344", "42", "session-B", set_active=False)
        self.pm.set_active("+79992223344")

        # Status should use switched profile's session
        r = self._invoke("auth", "status")
        assert r.exit_code == 0
        assert self.client_manager._use_session_calls[-1] == "session-B"

        # Logout clears active profile session
        r = self._invoke("auth", "logout")
        assert r.exit_code == 0
        assert self.pm.load_session(self.pm.get("+79992223344")) in (None, "")
