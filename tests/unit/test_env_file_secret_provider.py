"""Тесты EnvFileSecretProvider."""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch

from tg_exporter.secrets.env_file_secret_provider import EnvFileSecretProvider


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

    @patch("dotenv.dotenv_values", side_effect=ImportError)
    def test_dotenv_not_installed_fallback(self, mock_dotenv, tmp_path: Path):
        """Если python-dotenv не установлен — _values = {}."""
        env_file = tmp_path / ".env"
        env_file.write_text("TG_EXPORTER_TEST=hello\n")
        provider = EnvFileSecretProvider(env_file)
        assert provider.get("TG_EXPORTER_TEST") is None
