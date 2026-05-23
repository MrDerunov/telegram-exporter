"""Интеграционные тесты CLI-команд profile."""

from __future__ import annotations

from .test_cli_command_base import TestCliCommandBase


class _TestProfileBase(TestCliCommandBase):
    """Базовый класс для тестов profile."""

    # ---- helpers ----

    def _add(self, phone="+79991112233", api_id="42", api_hash="abc", name=None):
        args = ["profile", "add", "--phone", phone, "--api-id", api_id, "--api-hash", api_hash]
        if name:
            args.extend(["--name", name])
        return self._invoke(*args)

    def _list(self):
        return self._invoke("profile", "list")

    def _remove(self, phone):
        return self._invoke("profile", "remove", "--phone", phone)

    def _switch(self, phone):
        return self._invoke("profile", "switch", "--phone", phone)


# ---------------------------------------------------------------------------
# profile add
# ---------------------------------------------------------------------------

class TestProfileAdd(_TestProfileBase):
    """Добавление профиля."""

    def test_adds_profile_and_makes_it_active(self):
        result = self._add()

        assert result.exit_code == 0
        assert not self.pm.is_empty()
        assert self.pm.active_phone() == "+79991112233"
        assert self.pm.get("+79991112233") is not None

    def test_add_second_profile_becomes_active(self):
        self._add(phone="+71111111111")
        self._add(phone="+72222222222")

        assert len(self.pm.list()) == 2
        assert self.pm.active_phone() == "+72222222222"

    def test_add_with_display_name(self):
        self._add(name="Личный")

        profile = self.pm.get("+79991112233")
        assert profile.display_name == "Личный"

    def test_saves_api_hash_to_secret_store(self):
        self._add(api_hash="my-secret-hash")

        from tg_exporter.settings.secrets import API_HASH
        assert self.fake_secrets.store.get(API_HASH) == "my-secret-hash"


# ---------------------------------------------------------------------------
# profile list
# ---------------------------------------------------------------------------

class TestProfileList(_TestProfileBase):
    """Список профилей."""

    def test_shows_empty_message_when_no_profiles(self):
        result = self._list()
        assert result.exit_code == 0

    def test_lists_all_profiles(self):
        self._add(phone="+71111111111")
        self._add(phone="+72222222222", name="Работа")

        result = self._list()

        assert result.exit_code == 0
        assert "+71111111111" in result.output
        assert "+72222222222" in result.output
        assert "Работа" in result.output


# ---------------------------------------------------------------------------
# profile remove
# ---------------------------------------------------------------------------

class TestProfileRemove(_TestProfileBase):
    """Удаление профиля."""

    def test_removes_profile(self):
        self._add(phone="+71111111111")

        result = self._remove("+71111111111")

        assert result.exit_code == 0
        assert self.pm.is_empty()

    def test_exit_1_when_profile_not_found(self):
        result = self._remove("+79990000000")
        assert result.exit_code != 0

    def test_switches_active_when_removing_current(self):
        self._add(phone="+71111111111")
        self._add(phone="+72222222222")

        self._remove("+72222222222")

        assert self.pm.active_phone() == "+71111111111"


# ---------------------------------------------------------------------------
# profile switch
# ---------------------------------------------------------------------------

class TestProfileSwitch(_TestProfileBase):
    """Переключение активного профиля."""

    def test_switches_active_profile(self):
        self._add(phone="+71111111111")
        self._add(phone="+72222222222")

        result = self._switch("+71111111111")

        assert result.exit_code == 0
        assert self.pm.active_phone() == "+71111111111"

    def test_exit_1_when_profile_not_found(self):
        result = self._switch("+79990000000")
        assert result.exit_code != 0
