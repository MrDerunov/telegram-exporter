"""Интеграционные тесты взаимодействия auth-команд с профилями."""

from __future__ import annotations

from .test_cli_command_base import TestCliCommandBase


class TestAuthProfileInteraction(TestCliCommandBase):
    """Тесты совместной работы auth + profile команд."""

    # ------------------------------------------------------------------
    # auth status → использует сессию активного профиля (если есть)
    # ------------------------------------------------------------------

    def test_status_uses_active_profile_session(self):
        """auth status загружает сессию активного профиля."""
        self.pm.add_or_update("+79991112233", "42", "my-session-token")
        self.server.auth.set_authorized(True)

        result = self._invoke("auth", "status")

        assert result.exit_code == 0
        assert self.client_manager._use_session_calls[-1] == "my-session-token"

    def test_status_when_no_active_profile_still_works(self):
        """auth status работает без профиля (обратная совместимость)."""
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
    # auth logout — не трогает профили
    # ------------------------------------------------------------------

    def test_logout_does_not_touch_profiles(self):
        """auth logout не удаляет и не меняет профили."""
        self.pm.add_or_update("+79991112233", "42", "session-token")
        self.server.auth.set_authorized(True)

        result = self._invoke("auth", "logout")

        assert result.exit_code == 0
        assert not self.server.auth.is_authorized()
        assert self.pm.get("+79991112233") is not None
        assert self.pm.load_session(self.pm.get("+79991112233")) == "session-token"

    def test_logout_when_no_active_profile_still_works(self):
        """auth logout работает без профиля (обратная совместимость)."""
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
    # Полный цикл с профилями: login → add профиль → switch → status → logout
    # ------------------------------------------------------------------

    def test_full_cycle_with_profiles(self):
        """Полный цикл: login, ручное добавление профиля, switch, status, logout."""
        self.server.auth.set_authorized(False)

        # Login глобально, без профиля
        r = self._invoke("auth", "login", "--phone", "+79991112233",
                         "--api-id", "42", "--api-hash", "abc",
                         input="12345\n")
        assert r.exit_code == 0
        assert self.server.auth.is_authorized()
        assert self.pm.is_empty()

        # Вручную добавляем профиль через ProfileManager
        self.pm.add_or_update("+79991112233", "42", "session-after-login", display_name="Main")
        assert self.pm.active_phone() == "+79991112233"

        # Добавляем второй профиль и переключаемся
        self.pm.add_or_update("+79992223344", "42", "session-B", set_active=False)
        self.pm.set_active("+79992223344")

        # Status использует сессию переключённого профиля
        r = self._invoke("auth", "status")
        assert r.exit_code == 0
        assert self.client_manager._use_session_calls[-1] == "session-B"

        # Logout не трогает профили
        r = self._invoke("auth", "logout")
        assert r.exit_code == 0
        assert not self.server.auth.is_authorized()
        assert len(self.pm.list()) == 2
