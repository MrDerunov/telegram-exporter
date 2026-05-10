"""Tests for ProfileManager — хранение, CRUD, активный профиль, сессии через ISecretStore."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Optional

from tg_exporter.secrets.secret_store import ISecretStore
from tg_exporter.hosting.settings_store import ISettingsStore
from tg_exporter.hosting.state_model import StateModel


class _FakeSecretStore(ISecretStore):
    """In-memory замена ISecretStore для изоляции тестов."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str) -> Optional[str]:
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


class TestProfileManager(unittest.TestCase):

    def setUp(self):
        self._secrets = _FakeSecretStore()
        self._settings = _FakeSettingsStore()
        from tg_exporter.telegram.profiles import ProfileManager
        self.pm = ProfileManager(self._secrets, self._settings)

    def test_empty_initial_state(self):
        self.assertTrue(self.pm.is_empty())
        self.assertIsNone(self.pm.active())
        self.assertEqual(self.pm.list(), [])

    def test_add_and_list(self):
        p = self.pm.add_or_update(
            phone="+79991112233", api_id="42",
            session_string="session-A", display_name="Max",
        )
        self.assertEqual(p.phone, "+79991112233")
        self.assertEqual(p.display_name, "Max")
        self.assertFalse(self.pm.is_empty())
        self.assertEqual(self.pm.active_phone(), "+79991112233")
        self.assertEqual(len(self.pm.list()), 1)

    def test_session_stored_in_secret_store(self):
        self.pm.add_or_update(
            phone="+79991112233", api_id="42",
            session_string="session-A",
        )
        key = "42:session:+79991112233"
        self.assertEqual(self._secrets.store.get(key), "session-A")

    def test_add_second_profile_preserves_active(self):
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        self.pm.add_or_update(
            phone="+72222222222", api_id="42",
            session_string="s2", set_active=False,
        )
        self.assertEqual(len(self.pm.list()), 2)
        self.assertEqual(self.pm.active_phone(), "+71111111111")

    def test_set_active_switches(self):
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        self.pm.add_or_update(
            phone="+72222222222", api_id="42",
            session_string="s2", set_active=False,
        )
        result = self.pm.set_active("+72222222222")
        self.assertIsNotNone(result)
        self.assertEqual(self.pm.active_phone(), "+72222222222")

    def test_set_active_unknown_returns_none(self):
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        self.assertIsNone(self.pm.set_active("+70000000000"))
        self.assertEqual(self.pm.active_phone(), "+71111111111")

    def test_remove_deletes_session(self):
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        self.pm.add_or_update(
            phone="+72222222222", api_id="42",
            session_string="s2", set_active=False,
        )
        self.assertTrue(self.pm.remove("+71111111111"))
        # Активный должен переключиться на оставшийся
        self.assertEqual(self.pm.active_phone(), "+72222222222")
        # Сессия удалена из SecretStore
        self.assertNotIn("42:session:+71111111111", self._secrets.store)

    def test_remove_last_clears_active(self):
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        self.pm.remove("+71111111111")
        self.assertIsNone(self.pm.active_phone())
        self.assertTrue(self.pm.is_empty())

    def test_remove_unknown_returns_false(self):
        self.assertFalse(self.pm.remove("+70000000000"))

    def test_rename(self):
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        self.assertTrue(self.pm.rename("+71111111111", "Работа"))
        self.assertEqual(self.pm.get("+71111111111").display_name, "Работа")

    def test_load_session_roundtrip(self):
        p = self.pm.add_or_update(
            phone="+71111111111", api_id="42",
            session_string="my-session-string",
        )
        self.assertEqual(self.pm.load_session(p), "my-session-string")

    def test_persistence_across_instances(self):
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        self.pm.add_or_update(
            phone="+72222222222", api_id="42",
            session_string="s2", set_active=False,
        )
        self.pm.set_active("+72222222222")

        from tg_exporter.telegram.profiles import ProfileManager
        pm2 = ProfileManager(self._secrets, self._settings)
        self.assertEqual(pm2.active_phone(), "+72222222222")
        self.assertEqual(len(pm2.list()), 2)

    def test_phone_normalization(self):
        p = self.pm.add_or_update(
            phone="7 999 111-22-33", api_id="42", session_string="s",
        )
        self.assertEqual(p.phone, "79991112233")

    def test_empty_phone_raises(self):
        with self.assertRaises(ValueError):
            self.pm.add_or_update(phone="   ", api_id="42", session_string="s")

    def test_empty_api_id_raises(self):
        with self.assertRaises(ValueError):
            self.pm.add_or_update(phone="+71111111111", api_id="", session_string="s")

    def test_update_existing_keeps_phone(self):
        self.pm.add_or_update(
            phone="+71111111111", api_id="42",
            session_string="v1", display_name="Old",
        )
        updated = self.pm.add_or_update(
            phone="+71111111111", api_id="42",
            session_string="v2", display_name="New",
        )
        self.assertEqual(updated.display_name, "New")
        self.assertEqual(len(self.pm.list()), 1)
        key = "42:session:+71111111111"
        self.assertEqual(self._secrets.store.get(key), "v2")

    def test_state_has_no_session_secrets(self):
        self.pm.add_or_update(
            phone="+71111111111", api_id="42",
            session_string="super-secret-session",
        )
        state = self._settings.load()
        # Сессий в StateModel быть не должно
        self.assertEqual(state.active_phone, "+71111111111")
        self.assertEqual(len(state.profiles), 1)
        self.assertEqual(state.profiles[0].phone, "+71111111111")

    def test_chats_preserved_in_state(self):
        from tg_exporter.hosting.state_model import ChatEntry
        # Предустановка чатов через settings
        self._settings.save(StateModel(
            chats=(ChatEntry(name="Test", id=123),),
        ))
        # Добавляем профиль
        self.pm.add_or_update(phone="+71111111111", api_id="42", session_string="s1")
        # Чаты не должны быть затронуты
        state = self._settings.load()
        self.assertEqual(len(state.chats), 1)
        self.assertEqual(state.chats[0].id, 123)


if __name__ == "__main__":
    unittest.main()
