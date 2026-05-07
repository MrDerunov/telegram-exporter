"""Тесты SecretProvider и всех реализаций."""

from __future__ import annotations

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tg_exporter.secrets.secret_provider import SecretProvider
from tg_exporter.secrets.env_vars_secret_provider import EnvVarsSecretProvider
from tg_exporter.secrets.env_file_secret_provider import EnvFileSecretProvider
from tg_exporter.secrets.chain_secret_provider import ChainSecretProvider
from tg_exporter.secrets.keyring_secret_provider import KeyringSecretProvider


# ---------------------------------------------------------------------------
# SecretProvider ABC
# ---------------------------------------------------------------------------

class TestSecretProviderABC:
    def test_cannot_instantiate_abstract(self):
        """SecretProvider — абстрактный класс, нельзя создать напрямую."""
        with pytest.raises(TypeError):
            SecretProvider()  # type: ignore[abstract]

    def test_writable_default_is_false(self):
        """По умолчанию writable = False."""
        # Проверяем на уровне класса
        assert SecretProvider.writable is False


# ---------------------------------------------------------------------------
# EnvVarsSecretProvider
# ---------------------------------------------------------------------------

class TestEnvVarsSecretProvider:
    def test_get_set_delete(self):
        """Чтение, запись, удаление переменной."""
        provider = EnvVarsSecretProvider()
        provider.set("TEST_VAR", "test_value")
        assert provider.get("TEST_VAR") == "test_value"
        provider.delete("TEST_VAR")
        assert provider.get("TEST_VAR") is None

    def test_prefix_added(self):
        """Ключ автоматически получает префикс TG_EXPORTER_."""
        provider = EnvVarsSecretProvider()
        provider.set("MY_KEY", "secret")
        # Проверяем, что в окружении лежит с префиксом
        assert os.environ.get("TG_EXPORTER_MY_KEY") == "secret"
        provider.delete("MY_KEY")

    def test_get_missing_returns_none(self):
        """Отсутствующая переменная → None."""
        provider = EnvVarsSecretProvider()
        result = provider.get("NONEXISTENT_KEY_99999")
        assert result is None

    def test_delete_missing_does_not_crash(self):
        """delete() несуществующей переменной не падает."""
        provider = EnvVarsSecretProvider()
        provider.delete("DOES_NOT_EXIST_99999")

    def test_writable_is_true(self):
        """EnvVars провайдер — writable."""
        provider = EnvVarsSecretProvider()
        assert provider.writable is True

    def test_overwrite_existing(self):
        """Перезапись существующей переменной."""
        provider = EnvVarsSecretProvider()
        provider.set("OVERWRITE_TEST", "v1")
        provider.set("OVERWRITE_TEST", "v2")
        assert provider.get("OVERWRITE_TEST") == "v2"
        provider.delete("OVERWRITE_TEST")


# ---------------------------------------------------------------------------
# EnvFileSecretProvider
# ---------------------------------------------------------------------------

class TestEnvFileSecretProvider:
    def test_read_existing_key(self, tmp_path: Path):
        """Чтение существующего ключа из .env файла."""
        env_file = tmp_path / ".env"
        env_file.write_text("TG_EXPORTER_TEST=hello\nTG_EXPORTER_OTHER=world\n")
        provider = EnvFileSecretProvider(env_file)
        assert provider.get("TG_EXPORTER_TEST") == "hello"
        assert provider.get("TG_EXPORTER_OTHER") == "world"

    def test_missing_key_returns_none(self, tmp_path: Path):
        """Отсутствующий ключ → None."""
        env_file = tmp_path / ".env"
        env_file.write_text("TG_EXPORTER_TEST=hello\n")
        provider = EnvFileSecretProvider(env_file)
        assert provider.get("TG_EXPORTER_MISSING") is None

    def test_writable_is_false(self, tmp_path: Path):
        """EnvFile провайдер не поддерживает запись."""
        env_file = tmp_path / ".env"
        env_file.write_text("")
        provider = EnvFileSecretProvider(env_file)
        assert provider.writable is False

    def test_set_raises_not_implemented(self, tmp_path: Path):
        """set() кидает NotImplementedError."""
        env_file = tmp_path / ".env"
        env_file.write_text("")
        provider = EnvFileSecretProvider(env_file)
        with pytest.raises(NotImplementedError):
            provider.set("ANY", "value")

    def test_delete_is_noop(self, tmp_path: Path):
        """delete() ничего не делает и не падает."""
        env_file = tmp_path / ".env"
        env_file.write_text("TG_EXPORTER_TEST=hello\n")
        provider = EnvFileSecretProvider(env_file)
        provider.delete("TG_EXPORTER_TEST")
        # После delete значение всё ещё доступно
        assert provider.get("TG_EXPORTER_TEST") == "hello"

    def test_empty_file(self, tmp_path: Path):
        """Пустой файл — все get() возвращают None."""
        env_file = tmp_path / ".env"
        env_file.write_text("")
        provider = EnvFileSecretProvider(env_file)
        assert provider.get("ANY") is None

    def test_file_with_comments_and_blanks(self, tmp_path: Path):
        """Файл с комментариями и пустыми строками."""
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nTG_EXPORTER_A=a\n  \nTG_EXPORTER_B=b\n")
        provider = EnvFileSecretProvider(env_file)
        assert provider.get("TG_EXPORTER_A") == "a"
        assert provider.get("TG_EXPORTER_B") == "b"

    @patch("tg_exporter.secrets.env_file_secret_provider.dotenv_values", side_effect=ImportError)
    def test_dotenv_not_installed_fallback(self, mock_dotenv, tmp_path: Path):
        """Если python-dotenv не установлен — _values = {}."""
        env_file = tmp_path / ".env"
        env_file.write_text("TG_EXPORTER_TEST=hello\n")
        provider = EnvFileSecretProvider(env_file)
        # Все get() вернут None, потому что dotenv не смог загрузиться
        assert provider.get("TG_EXPORTER_TEST") is None


# ---------------------------------------------------------------------------
# ChainSecretProvider
# ---------------------------------------------------------------------------

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
        # ev не имеет значения
        env_file = Path("/nonexistent/.env")
        ef = EnvFileSecretProvider(env_file)
        # ef тоже не найдёт (файла нет)
        chain = ChainSecretProvider([ev, ef])
        assert chain.get("MISSING") is None

    def test_set_writes_to_all_writable(self):
        """set() пишет во все writable провайдеры."""
        ev = EnvVarsSecretProvider()  # writable=True
        env_file = Path("/nonexistent/.env")
        ef = EnvFileSecretProvider(env_file)  # writable=False
        chain = ChainSecretProvider([ev, ef])
        chain.set("WRITE_TEST", "chain_value")
        # EnvVars должен получить
        assert ev.get("WRITE_TEST") == "chain_value"
        # EnvFile НЕ должен (writable=False, set() raises NotImplementedError)
        # Значение не должно быть записано в ef
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
        # Это классовое поле, всегда True
        assert ChainSecretProvider.writable is True

    def test_empty_chain_get_returns_none(self):
        """Пустая цепочка: get() → None."""
        chain = ChainSecretProvider([])
        assert chain.get("ANY") is None

    def test_empty_chain_set_does_not_crash(self):
        """Пустая цепочка: set() не падает (просто некуда писать)."""
        chain = ChainSecretProvider([])
        chain.set("ANY", "value")  # не должен падать

    def test_empty_chain_delete_does_not_crash(self):
        """Пустая цепочка: delete() не падает."""
        chain = ChainSecretProvider([])
        chain.delete("ANY")  # не должен падать

    def test_chain_order_respected(self):
        """Порядок провайдеров в цепочке соблюдается."""
        ev1 = EnvVarsSecretProvider()
        ev2 = EnvVarsSecretProvider()
        ev1.set("ORDER_KEY", "first")
        ev2.set("ORDER_KEY", "second")
        chain = ChainSecretProvider([ev1, ev2])
        # Первый провайдер возвращает "first"
        assert chain.get("ORDER_KEY") == "first"
        ev1.delete("ORDER_KEY")
        ev2.delete("ORDER_KEY")

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


# ---------------------------------------------------------------------------
# KeyringSecretProvider
# ---------------------------------------------------------------------------

class TestKeyringSecretProvider:
    def test_writable_is_true(self):
        """Keyring провайдер поддерживает запись."""
        provider = KeyringSecretProvider()
        assert provider.writable is True

    def test_get_returns_value(self):
        """get() возвращает значение через keyring."""
        with patch("tg_exporter.secrets.keyring_secret_provider.keyring") as mock_kr:
            mock_kr.get_password.return_value = "my_secret"
            provider = KeyringSecretProvider()
            assert provider.get("api_hash") == "my_secret"
            mock_kr.get_password.assert_called_once_with("tg_exporter", "api_hash")

    def test_get_returns_none_when_not_found(self):
        """get() → None если секрета нет."""
        with patch("tg_exporter.secrets.keyring_secret_provider.keyring") as mock_kr:
            mock_kr.get_password.return_value = None
            provider = KeyringSecretProvider()
            assert provider.get("missing") is None

    def test_get_handles_exception(self):
        """get() не падает при ошибке keyring."""
        with patch("tg_exporter.secrets.keyring_secret_provider.keyring") as mock_kr:
            mock_kr.get_password.side_effect = RuntimeError("keyring error")
            provider = KeyringSecretProvider()
            result = provider.get("api_hash")
            assert result is None  # gracefully returns None

    def test_set_calls_keyring(self):
        """set() вызывает keyring.set_password."""
        with patch("tg_exporter.secrets.keyring_secret_provider.keyring") as mock_kr:
            provider = KeyringSecretProvider()
            provider.set("api_hash", "abc123")
            mock_kr.set_password.assert_called_once_with("tg_exporter", "api_hash", "abc123")

    def test_set_handles_exception(self):
        """set() не падает при ошибке keyring."""
        with patch("tg_exporter.secrets.keyring_secret_provider.keyring") as mock_kr:
            mock_kr.set_password.side_effect = RuntimeError("keyring error")
            provider = KeyringSecretProvider()
            provider.set("api_hash", "value")  # не падает

    def test_delete_calls_keyring(self):
        """delete() вызывает keyring.delete_password."""
        with patch("tg_exporter.secrets.keyring_secret_provider.keyring") as mock_kr:
            provider = KeyringSecretProvider()
            provider.delete("api_hash")
            mock_kr.delete_password.assert_called_once_with("tg_exporter", "api_hash")

    def test_delete_handles_exception(self):
        """delete() не падает при ошибке keyring."""
        with patch("tg_exporter.secrets.keyring_secret_provider.keyring") as mock_kr:
            mock_kr.delete_password.side_effect = RuntimeError("keyring error")
            provider = KeyringSecretProvider()
            provider.delete("api_hash")  # не падает
