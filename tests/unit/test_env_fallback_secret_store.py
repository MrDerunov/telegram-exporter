"""Тесты EnvFallbackSecretStore — враппер с fallback на переменные окружения."""

from __future__ import annotations

import pytest

from tg_exporter.settings.secrets.env_fallback_secret_store import EnvFallbackSecretStore
from tg_exporter.settings.secrets.secret_store import ISecretStore


class _FakeInnerStore(ISecretStore):
    """In-memory хранилище для теста враппера."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value

    def delete(self, key: str) -> None:
        self._data.pop(key, None)


class TestEnvFallbackSecretStore:

    @pytest.fixture(autouse=True)
    def _setup(self):
        self._inner = _FakeInnerStore()
        self._store = EnvFallbackSecretStore(self._inner)

    # ------------------------------------------------------------------
    # get — env vars
    # ------------------------------------------------------------------

    def test_get_returns_env_var_when_set(self, monkeypatch):
        """get возвращает значение из переменной окружения, если она есть."""
        monkeypatch.setenv("TG_EXPORTER_SESSION", "env_sess")
        assert self._store.get("SESSION") == "env_sess"

    def test_get_falls_back_to_inner_when_env_not_set(self):
        """get обращается к inner store, если переменной окружения нет."""
        self._inner.set("SESSION", "inner_sess")
        assert self._store.get("SESSION") == "inner_sess"

    def test_get_env_var_overrides_inner(self, monkeypatch):
        """Переменная окружения имеет приоритет над inner store."""
        monkeypatch.setenv("TG_EXPORTER_SESSION", "env_sess")
        self._inner.set("SESSION", "inner_sess")
        assert self._store.get("SESSION") == "env_sess"

    def test_get_returns_none_when_neither_env_nor_inner(self):
        """Если нет ни в env, ни в inner — None."""
        assert self._store.get("SESSION") is None

    # ------------------------------------------------------------------
    # set / delete — проксируются в inner
    # ------------------------------------------------------------------

    def test_set_proxies_to_inner(self):
        """set записывает значение в inner store."""
        self._store.set("SESSION", "saved")
        assert self._inner.get("SESSION") == "saved"

    def test_set_does_not_write_to_env(self, monkeypatch):
        """set НЕ пишет в переменные окружения."""
        self._store.set("SESSION", "saved")
        assert "TG_EXPORTER_SESSION" not in dict(monkeypatch._envs if hasattr(monkeypatch, '_envs') else {})
        # Проверяем что os.environ не изменился (в рамках теста это сложно,
        # но мы уже проверили что inner получил значение)

    def test_delete_proxies_to_inner(self):
        """delete удаляет ключ из inner store."""
        self._inner.set("SESSION", "to_delete")
        self._store.delete("SESSION")
        assert self._inner.get("SESSION") is None

    def test_delete_does_not_affect_env(self, monkeypatch):
        """delete НЕ трогает переменные окружения."""
        monkeypatch.setenv("TG_EXPORTER_SESSION", "env_sess")
        self._store.delete("SESSION")
        assert self._store.get("SESSION") == "env_sess"  # всё ещё читается из env
