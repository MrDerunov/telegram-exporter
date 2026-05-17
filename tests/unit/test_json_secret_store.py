"""Тесты JsonSecretStore — хранение секретов в файле."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tg_exporter.secrets.json_secret_store import JsonSecretStore


class TestJsonSecretStore:

    @staticmethod
    def _store(tmp_path: Path) -> JsonSecretStore:
        return JsonSecretStore(tmp_path)

    # ------------------------------------------------------------------
    # get
    # ------------------------------------------------------------------

    def test_return_none_for_missing_key(self, tmp_path: Path):
        """get возвращает None для отсутствующего ключа."""
        store = self._store(tmp_path)
        assert store.get("nonexistent") is None

    def test_return_value_for_existing_key(self, tmp_path: Path):
        """get возвращает значение для существующего ключа."""
        store = self._store(tmp_path)
        store.set("token", "abc123")
        assert store.get("token") == "abc123"

    # ------------------------------------------------------------------
    # set
    # ------------------------------------------------------------------

    def test_set_and_get_roundtrip(self, tmp_path: Path):
        """set сохраняет значение, get его возвращает."""
        store = self._store(tmp_path)
        store.set("api_id", "42")
        assert store.get("api_id") == "42"

    def test_set_overwrites_existing_value(self, tmp_path: Path):
        """Повторный set перезаписывает значение."""
        store = self._store(tmp_path)
        store.set("key", "v1")
        store.set("key", "v2")
        assert store.get("key") == "v2"

    # ------------------------------------------------------------------
    # delete
    # ------------------------------------------------------------------

    def test_delete_removes_key(self, tmp_path: Path):
        """delete удаляет ключ, get возвращает None."""
        store = self._store(tmp_path)
        store.set("token", "secret")
        store.delete("token")
        assert store.get("token") is None

    def test_delete_unknown_key_does_not_raise(self, tmp_path: Path):
        """delete несуществующего ключа не вызывает ошибок."""
        store = self._store(tmp_path)
        store.delete("phantom")

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def test_persist_across_instances(self, tmp_path: Path):
        """Данные сохраняются между разными экземплярами с одним config_dir."""
        store1 = self._store(tmp_path)
        store1.set("session", "xyz")

        store2 = self._store(tmp_path)
        assert store2.get("session") == "xyz"

    def test_writes_to_secrets_json_in_config_dir(self, tmp_path: Path):
        """Файл secrets.json создаётся в config_dir."""
        store = self._store(tmp_path)
        store.set("k", "v")
        secrets_path = tmp_path / "secrets.json"
        assert secrets_path.exists()
        data = json.loads(secrets_path.read_text())
        assert data["k"] == "v"

    # ------------------------------------------------------------------
    # edge cases
    # ------------------------------------------------------------------

    def test_handles_corrupted_file(self, tmp_path: Path):
        """Повреждённый JSON не вызывает падения, возвращается пустой результат."""
        secrets_path = tmp_path / "secrets.json"
        secrets_path.write_text("not valid {{{")
        store = self._store(tmp_path)
        assert store.get("any") is None

    def test_filters_non_string_values(self, tmp_path: Path):
        """Нестроковые значения в JSON игнорируются при чтении."""
        secrets_path = tmp_path / "secrets.json"
        secrets_path.write_text(json.dumps({"str_key": "ok", "int_key": 42, "null_key": None}))
        store = self._store(tmp_path)
        assert store.get("str_key") == "ok"
        assert store.get("int_key") is None
        assert store.get("null_key") is None
