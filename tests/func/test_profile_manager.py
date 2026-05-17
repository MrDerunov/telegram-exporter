"""Tests for ProfileManager — хранение, CRUD, активный профиль, сессии через ISecretStore."""

from __future__ import annotations

import pytest

from tg_exporter.secrets.secret_store import ISecretStore
from tg_exporter.configs.settings_store import ISettingsStore
from tg_exporter.configs.state_model import StateModel


class _FakeSecretStore(ISecretStore):
    """In-memory замена ISecretStore для изоляции тестов."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(self, key: str, value: str) -> None:
        self.store[key] = value

    def delete(self, key: str) -> None:
        self.store.pop(key, None)


class _FakeSettingsStore(ISettingsStore):
    """In-memory замена ISettingsStore для изоляции тестов."""

    def __init__(self) -> None:
        self._state = StateModel()

    def load(self) -> StateModel:
        return self._state

    def save(self, state: StateModel) -> None:
        self._state = state


class TestProfileManager:

    @pytest.fixture(autouse=True)
    def _setup(self):
        self._secrets = _FakeSecretStore()
        self._settings = _FakeSettingsStore()
        from tg_exporter.services.telegram import ProfileManager
        self.pm = ProfileManager(self._secrets, self._settings)

    def test_have_empty_state_initially(self):
        """ProfileManager при создании не содержит профилей."""
        assert self.pm.is_empty()
        assert self.pm.active() is None
        assert self.pm.list() == []

    def test_add_profile_and_list_it(self):
        """Добавленный профиль появляется в списке и становится активным."""
        p = self.pm.add_or_update(
            phone="+79991112233", api_id="42",
            session_string="session-A", display_name="Max",
        )
        assert p.phone == "+79991112233"
        assert p.display_name == "Max"
        assert not self.pm.is_empty()
        assert self.pm.active_phone() == "+79991112233"
        assert len(self.pm.list()) == 1

    def test_store_session_in_secret_store(self):
        """Сессия сохраняется в ISecretStore."""
        self.pm.add_or_update(
            phone="+79991112233", api_id="42",
            session_string="session-A",
        )
        key = "42:session:+79991112233"
        assert self._secrets.store.get(key) == "session-A"

    def test_preserve_active_profile_when_adding_second(self):
        """Добавление второго профиля без set_active не меняет активный."""
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        self.pm.add_or_update(
            phone="+72222222222", api_id="42",
            session_string="s2", set_active=False,
        )
        assert len(self.pm.list()) == 2
        assert self.pm.active_phone() == "+71111111111"

    def test_switch_active_profile(self):
        """set_active переключает активный профиль."""
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        self.pm.add_or_update(
            phone="+72222222222", api_id="42",
            session_string="s2", set_active=False,
        )
        result = self.pm.set_active("+72222222222")
        assert result is not None
        assert self.pm.active_phone() == "+72222222222"

    def test_return_none_when_setting_active_for_unknown_phone(self):
        """set_active для неизвестного телефона возвращает None."""
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        assert self.pm.set_active("+70000000000") is None
        assert self.pm.active_phone() == "+71111111111"

    def test_delete_session_on_remove(self):
        """Удаление профиля удаляет его сессию из SecretStore."""
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        self.pm.add_or_update(
            phone="+72222222222", api_id="42",
            session_string="s2", set_active=False,
        )
        assert self.pm.remove("+71111111111")
        assert self.pm.active_phone() == "+72222222222"
        assert "42:session:+71111111111" not in self._secrets.store

    def test_clear_active_when_removing_last_profile(self):
        """Удаление последнего профиля сбрасывает активный."""
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        self.pm.remove("+71111111111")
        assert self.pm.active_phone() is None
        assert self.pm.is_empty()

    def test_return_false_when_removing_unknown_profile(self):
        """Удаление несуществующего профиля возвращает False."""
        assert not self.pm.remove("+70000000000")

    def test_rename_profile(self):
        """Переименование профиля меняет display_name."""
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        assert self.pm.rename("+71111111111", "Работа")
        assert self.pm.get("+71111111111").display_name == "Работа"

    def test_load_session_roundtrip(self):
        """Сохранённая сессия корректно загружается."""
        p = self.pm.add_or_update(
            phone="+71111111111", api_id="42",
            session_string="my-session-string",
        )
        assert self.pm.load_session(p) == "my-session-string"

    def test_persist_state_across_instances(self):
        """Состояние сохраняется при создании нового экземпляра ProfileManager."""
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        self.pm.add_or_update(
            phone="+72222222222", api_id="42",
            session_string="s2", set_active=False,
        )
        self.pm.set_active("+72222222222")

        from tg_exporter.services.telegram import ProfileManager
        pm2 = ProfileManager(self._secrets, self._settings)
        assert pm2.active_phone() == "+72222222222"
        assert len(pm2.list()) == 2

    def test_normalize_phone(self):
        """Телефон нормализуется (удаляются пробелы и спецсимволы)."""
        p = self.pm.add_or_update(
            phone="7 999 111-22-33", api_id="42", session_string="s",
        )
        assert p.phone == "79991112233"

    def test_throw_when_phone_is_empty(self):
        """Пустой телефон вызывает ValueError."""
        with pytest.raises(ValueError):
            self.pm.add_or_update(phone="   ", api_id="42", session_string="s")

    def test_throw_when_api_id_is_empty(self):
        """Пустой api_id вызывает ValueError."""
        with pytest.raises(ValueError):
            self.pm.add_or_update(phone="+71111111111", api_id="", session_string="s")

    def test_update_existing_profile(self):
        """Обновление существующего профиля меняет данные и сессию."""
        self.pm.add_or_update(
            phone="+71111111111", api_id="42",
            session_string="v1", display_name="Old",
        )
        updated = self.pm.add_or_update(
            phone="+71111111111", api_id="42",
            session_string="v2", display_name="New",
        )
        assert updated.display_name == "New"
        assert len(self.pm.list()) == 1
        key = "42:session:+71111111111"
        assert self._secrets.store.get(key) == "v2"

    def test_not_store_session_in_state_model(self):
        """Сессии не должны храниться в StateModel (только в SecretStore)."""
        self.pm.add_or_update(
            phone="+71111111111", api_id="42",
            session_string="super-secret-session",
        )
        state = self._settings.load()
        assert state.active_phone == "+71111111111"
        assert len(state.profiles) == 1
        assert state.profiles[0].phone == "+71111111111"

    def test_preserve_chats_when_adding_profile(self):
        """Добавление профиля не затрагивает существующие чаты в StateModel."""
        from tg_exporter.configs.state_model import ChatEntry
        self._settings.save(StateModel(
            chats=(ChatEntry(name="Test", id=123),),
        ))
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        state = self._settings.load()
        assert len(state.chats) == 1
        assert state.chats[0].id == 123
