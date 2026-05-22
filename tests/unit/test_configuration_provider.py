"""Тесты ConfigurationProvider — сборка конфигурации из источников."""

from __future__ import annotations

import json
from pathlib import Path

from tg_exporter.settings.configuration_provider import (
    resolve_config_dir,
    _merge_dicts,
    _load_json,
    _load_dotenv,
    _load_env_vars,
    build_merged_config,
    ConfigurationProvider,
    ConfigurationResult,
)


# ---------------------------------------------------------------------------
# resolve_config_dir
# ---------------------------------------------------------------------------

class TestResolveConfigDir:
    def test_return_env_dir_when_set(self, monkeypatch, tmp_path: Path):
        """При установленной TELEGRAM_EXPORTER_CONFIG_DIR возвращает её значение."""
        monkeypatch.setenv("TELEGRAM_EXPORTER_CONFIG_DIR", str(tmp_path))
        result = resolve_config_dir()
        assert result == tmp_path.resolve()

    def test_return_cwd_when_env_not_set(self, monkeypatch):
        """Без переменной окружения возвращает текущую рабочую директорию."""
        monkeypatch.delenv("TELEGRAM_EXPORTER_CONFIG_DIR", raising=False)
        result = resolve_config_dir()
        assert result == Path.cwd()


# ---------------------------------------------------------------------------
# _merge_dicts
# ---------------------------------------------------------------------------

class TestMergeDicts:
    def test_add_new_keys_from_override(self):
        """Новые ключи из override добавляются в base."""
        base = {"a": 1}
        result = _merge_dicts(base, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_override_existing_keys(self):
        """Существующие ключи переопределяются значениями из override."""
        base = {"a": 1, "b": 2}
        result = _merge_dicts(base, {"a": 99})
        assert result == {"a": 99, "b": 2}

    def test_not_override_with_empty_string(self):
        """Пустая строка не переопределяет непустое значение."""
        base = {"a": "hello"}
        result = _merge_dicts(base, {"a": ""})
        assert result == {"a": "hello"}

    def test_merge_nested_dicts_recursively(self):
        """Вложенные словари мерджатся рекурсивно."""
        base = {"nested": {"x": 1, "y": 2}}
        override = {"nested": {"y": 99, "z": 3}}
        result = _merge_dicts(base, override)
        assert result == {"nested": {"x": 1, "y": 99, "z": 3}}

    def test_not_override_nested_with_empty_value(self):
        """Пустое значение во вложенном словаре не затирает непустое."""
        base = {"nested": {"x": 1}}
        result = _merge_dicts(base, {"nested": {"x": ""}})
        assert result == {"nested": {"x": 1}}

    def test_handle_empty_override(self):
        """Пустой override не меняет base."""
        base = {"a": 1}
        result = _merge_dicts(base, {})
        assert result == {"a": 1}


# ---------------------------------------------------------------------------
# _load_json
# ---------------------------------------------------------------------------

class TestLoadJson:
    def test_load_valid_json_file(self, tmp_path: Path):
        """Валидный JSON-файл загружается корректно."""
        file_path = tmp_path / "config.json"
        file_path.write_text(json.dumps({"key": "value"}))
        result = _load_json(file_path)
        assert result == {"key": "value"}

    def test_return_empty_dict_when_file_does_not_exist(self, tmp_path: Path):
        """Отсутствующий файл — возвращает {}."""
        result = _load_json(tmp_path / "nonexistent.json")
        assert result == {}

    def test_return_empty_dict_on_corrupted_json(self, tmp_path: Path):
        """Повреждённый JSON возвращает {} без падения."""
        file_path = tmp_path / "bad.json"
        file_path.write_text("not valid {{{")
        result = _load_json(file_path)
        assert result == {}

    def test_return_empty_dict_for_empty_json_object(self, tmp_path: Path):
        """Пустой JSON объект {} возвращается как {}."""
        file_path = tmp_path / "empty.json"
        file_path.write_text("{}")
        result = _load_json(file_path)
        assert result == {}


# ---------------------------------------------------------------------------
# _load_dotenv
# ---------------------------------------------------------------------------

class TestLoadDotenv:
    def test_load_dotenv_file(self, tmp_path: Path, monkeypatch):
        """.env файл с переменными загружается."""
        env_file = tmp_path / ".env"
        env_file.write_text("TG_EXPORTER_API_ID=123\nKEY=value\n")
        result = _load_dotenv(env_file)
        assert result.get("api_id") == "123"
        assert result.get("key") == "value"

    def test_return_empty_dict_when_file_does_not_exist(self, tmp_path: Path):
        """Отсутствующий .env файл возвращает {}."""
        result = _load_dotenv(tmp_path / "nonexistent.env")
        assert result == {}


# ---------------------------------------------------------------------------
# _load_env_vars
# ---------------------------------------------------------------------------

class TestLoadEnvVars:
    def test_load_env_vars_with_prefix(self, monkeypatch):
        """Переменные окружения с префиксом TG_EXPORTER_ загружаются."""
        monkeypatch.setenv("TG_EXPORTER_API_ID", "123")
        monkeypatch.setenv("TG_EXPORTER_SECRET", "abc")
        monkeypatch.setenv("OTHER_VAR", "ignored")
        result = _load_env_vars()
        assert result.get("api_id") == "123"
        assert result.get("secret") == "abc"
        assert "other_var" not in result

    def test_return_empty_dict_when_no_matching_vars(self, monkeypatch):
        """Без переменных с префиксом возвращает {}."""
        monkeypatch.setenv("OTHER_VAR", "value")
        result = _load_env_vars()
        assert result == {}


# ---------------------------------------------------------------------------
# build_merged_config
# ---------------------------------------------------------------------------

class TestBuildMergedConfig:
    def test_load_config_json(self, tmp_path: Path):
        """config.json загружается и попадает в результат."""
        (tmp_path / "config.json").write_text(json.dumps({"api_id": "42"}))
        result = build_merged_config(tmp_path)
        assert result.get("api_id") == "42"

    def test_env_vars_override_config_json(self, tmp_path: Path, monkeypatch):
        """Переменные окружения переопределяют config.json."""
        (tmp_path / "config.json").write_text(json.dumps({"api_id": "1"}))
        monkeypatch.setenv("TG_EXPORTER_API_ID", "999")
        result = build_merged_config(tmp_path)
        assert result.get("api_id") == "999"

    def test_dotenv_override_config_json(self, tmp_path: Path):
        """.env переопределяет config.json."""
        (tmp_path / "config.json").write_text(json.dumps({"api_id": "1"}))
        (tmp_path / ".env").write_text("TG_EXPORTER_API_ID=42\n")
        result = build_merged_config(tmp_path)
        assert result.get("api_id") == "42"

    def test_return_empty_dict_when_no_files(self, tmp_path: Path, monkeypatch):
        """При отсутствии всех источников возвращает {}."""
        monkeypatch.delenv("TG_EXPORTER_API_ID", raising=False)
        result = build_merged_config(tmp_path)
        assert result == {}

    def test_load_secrets_json(self, tmp_path: Path):
        """secrets.json загружается и попадает в результат."""
        (tmp_path / "secrets.json").write_text(json.dumps({"secret_key": "top_secret"}))
        result = build_merged_config(tmp_path)
        assert result.get("secret_key") == "top_secret"

    def test_load_state_json(self, tmp_path: Path):
        """state.json загружается и попадает в результат."""
        (tmp_path / "state.json").write_text(json.dumps({"active_phone": "+7999"}))
        result = build_merged_config(tmp_path)
        assert result.get("active_phone") == "+7999"


# ---------------------------------------------------------------------------
# ConfigurationProvider
# ---------------------------------------------------------------------------

class TestConfigurationProvider:
    def test_return_configuration_result(self, tmp_path: Path):
        """build() возвращает ConfigurationResult с сырым словарём."""
        (tmp_path / "config.json").write_text(json.dumps({"api_id": "42"}))
        provider = ConfigurationProvider(tmp_path)
        result = provider.build()
        assert isinstance(result, ConfigurationResult)
        assert result.raw.get("api_id") == "42"
        assert result.config_dir == tmp_path

    def test_contain_config_dir_in_result(self, tmp_path: Path):
        """ConfigurationResult содержит директорию конфигов."""
        provider = ConfigurationProvider(tmp_path)
        result = provider.build()
        assert result.config_dir == tmp_path
