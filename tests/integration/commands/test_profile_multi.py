"""Интеграционные тесты с несколькими профилями: добавление, переключение, удаление."""

from __future__ import annotations

from .test_cli_command_base import TestCliCommandBase


class TestProfileMulti(TestCliCommandBase):
    """Тесты с несколькими профилями в разных комбинациях."""

    def _add(self, phone="+79991112233", api_id="42", api_hash="abc", name=None):
        args = ["profile", "add", "--phone", phone, "--api-id", api_id, "--api-hash", api_hash]
        if name:
            args.extend(["--name", name])
        return self._invoke(*args)

    def _remove(self, phone):
        return self._invoke("profile", "remove", "--phone", phone)

    def _switch(self, phone):
        return self._invoke("profile", "switch", "--phone", phone)

    # ------------------------------------------------------------------

    def test_three_profiles_all_visible_in_list(self):
        """Три добавленных профиля отображаются в списке."""
        self._add(phone="+71111111111", name="A")
        self._add(phone="+72222222222", name="B")
        self._add(phone="+73333333333", name="C")

        profiles = self.pm.list()
        assert len(profiles) == 3
        assert self.pm.active_phone() == "+73333333333"

    def test_switch_between_three_profiles(self):
        """Переключение между тремя профилями."""
        self._add(phone="+71111111111", name="A")
        self._add(phone="+72222222222", name="B")
        self._add(phone="+73333333333", name="C")

        assert self._switch("+71111111111").exit_code == 0
        assert self.pm.active_phone() == "+71111111111"

        assert self._switch("+72222222222").exit_code == 0
        assert self.pm.active_phone() == "+72222222222"

        assert self._switch("+73333333333").exit_code == 0
        assert self.pm.active_phone() == "+73333333333"

    def test_remove_active_profile_switches_to_next(self):
        """При удалении активного профиля следующим становится первый из оставшихся."""
        self._add(phone="+71111111111", name="A")
        self._add(phone="+72222222222", name="B")
        self._add(phone="+73333333333", name="C")

        self._switch("+72222222222")
        self._remove("+72222222222")

        assert len(self.pm.list()) == 2
        assert self.pm.active_phone() == "+71111111111"

    def test_remove_all_profiles(self):
        """Удаление всех профилей приводит к пустому состоянию."""
        self._add(phone="+71111111111")
        self._add(phone="+72222222222")

        self._remove("+72222222222")
        self._remove("+71111111111")

        assert self.pm.is_empty()
        assert self.pm.active_phone() is None

    def test_update_profile_by_re_adding_same_phone(self):
        """Повторное добавление с тем же телефоном обновляет профиль."""
        self._add(phone="+79991112233", api_id="42", name="Old")

        result = self._add(phone="+79991112233", api_id="42", name="New")

        assert result.exit_code == 0
        assert len(self.pm.list()) == 1
        assert self.pm.get("+79991112233").display_name == "New"

    def test_remove_nonexistent_does_not_change_others(self):
        """Удаление несуществующего профиля не затрагивает существующие."""
        self._add(phone="+71111111111", name="A")
        self._add(phone="+72222222222", name="B")

        result = self._remove("+79990000000")

        assert result.exit_code != 0
        assert len(self.pm.list()) == 2
