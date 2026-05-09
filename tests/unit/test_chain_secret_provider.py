"""Тесты ChainSecretProvider."""
from __future__ import annotations

from pathlib import Path

from tg_exporter.secrets.env_vars_secret_provider import EnvVarsSecretProvider
from tg_exporter.secrets.env_file_secret_provider import EnvFileSecretProvider
from tg_exporter.secrets.chain_secret_provider import ChainSecretProvider


class TestChainSecretProvider:
    def test_get_first_non_none(self):
        """Chain.get() возвращает первое не-None значение."""
        ev = EnvVarsSecretProvider()
        ev.set("PRIORITY", "from_env")
        ef = EnvFileSecretProvider(Path("/nonexistent/.env"))
        chain = ChainSecretProvider([ev, ef])
        assert chain.get("PRIORITY") == "from_env"
        ev.delete("PRIORITY")

    def test_get_falls_through_to_next(self):
        """Если первый провайдер возвращает None, идём к следующему."""
        ev = EnvVarsSecretProvider()
        env_file = Path("/nonexistent/.env")
        ef = EnvFileSecretProvider(env_file)
        chain = ChainSecretProvider([ev, ef])
        assert chain.get("MISSING") is None

    def test_set_writes_to_all_writable(self):
        """set() пишет во все writable провайдеры."""
        ev = EnvVarsSecretProvider()
        env_file = Path("/nonexistent/.env")
        ef = EnvFileSecretProvider(env_file)
        chain = ChainSecretProvider([ev, ef])
        chain.set("WRITE_TEST", "chain_value")
        assert ev.get("WRITE_TEST") == "chain_value"
        ev.delete("WRITE_TEST")

    def test_delete_from_all_writable(self):
        """delete() удаляет из всех writable провайдеров."""
        ev = EnvVarsSecretProvider()
        ev.set("DEL_TEST", "to_delete")
        chain = ChainSecretProvider([ev])
        chain.delete("DEL_TEST")
        assert ev.get("DEL_TEST") is None

    def test_writable_flag_true_when_any_writable(self):
        """Chain.writable = True — классовый атрибут."""
        assert ChainSecretProvider.writable is True

    def test_empty_chain_get_returns_none(self):
        """Пустая цепочка: get() → None."""
        chain = ChainSecretProvider([])
        assert chain.get("ANY") is None

    def test_empty_chain_set_does_not_crash(self):
        """Пустая цепочка: set() не падает (просто некуда писать)."""
        chain = ChainSecretProvider([])
        chain.set("ANY", "value")

    def test_empty_chain_delete_does_not_crash(self):
        """Пустая цепочка: delete() не падает."""
        chain = ChainSecretProvider([])
        chain.delete("ANY")

    def test_chain_order_respected(self, tmp_path: Path):
        """Порядок провайдеров в цепочке соблюдается."""
        # Используем изолированные EnvFileSecretProvider с разными .env файлами,
        # чтобы избежать конфликта глобальных переменных окружения.
        env1 = tmp_path / "env1"
        env2 = tmp_path / "env2"
        env1.write_text("TG_EXPORTER_ORDER_KEY=first\n")
        env2.write_text("TG_EXPORTER_ORDER_KEY=second\n")
        ef1 = EnvFileSecretProvider(env1)
        ef2 = EnvFileSecretProvider(env2)
        chain = ChainSecretProvider([ef1, ef2])
        assert chain.get("TG_EXPORTER_ORDER_KEY") == "first"

    def test_multiple_writable_providers_all_receive_set(self):
        """set() доходит до всех writable провайдеров."""
        ev1 = EnvVarsSecretProvider()
        ev2 = EnvVarsSecretProvider()
        chain = ChainSecretProvider([ev1, ev2])
        chain.set("MULTI_KEY", "shared")
        assert ev1.get("MULTI_KEY") == "shared"
        assert ev2.get("MULTI_KEY") == "shared"
        ev1.delete("MULTI_KEY")
        ev2.delete("MULTI_KEY")
