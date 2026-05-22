"""ConfigurationProvider — собирает конфигурацию из всех источников в единый словарь.
НЕ маппит в типы — это делает хост. Возвращает ConfigurationResult с сырым словарём.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from tg_exporter.settings.secrets import _ENV_PREFIX

# Имя переменной окружения для определения директории конфигов
_CONFIG_DIR_ENV = "TELEGRAM_EXPORTER_CONFIG_DIR"


def resolve_config_dir() -> Path:
    """Определяет директорию конфигов.

    1. TELEGRAM_EXPORTER_CONFIG_DIR (переменная среды)
    2. ./ (текущая рабочая директория)
    """
    env_dir = os.environ.get(_CONFIG_DIR_ENV)
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return Path.cwd()


def _merge_dicts(base: dict, override: dict) -> dict:
    """Мерджит override в base. Пустые значения (None, "") НЕ переопределяют непустые."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _merge_dicts(base[key], value)
        elif value not in (None, "", [], {}):
            base[key] = value
    return base


def _load_json(path: Path) -> dict:
    """Читает JSON-файл. Возвращает {} если файл отсутствует или повреждён."""
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def _load_dotenv(path: Path) -> dict[str, str]:
    """Читает .env файл. Ключи приводятся к lowercase, префикс TG_EXPORTER_ снимается."""
    if not path.exists():
        return {}
    try:
        from dotenv import dotenv_values
        raw = dotenv_values(path)
    except ImportError:
        return {}
    result: dict[str, str] = {}
    prefix_lower = _ENV_PREFIX.lower()
    for k, v in raw.items():
        if v is None:
            continue
        key = k.lower()
        if key.startswith(prefix_lower):
            key = key[len(prefix_lower):]
        result[key] = v
    return result


def _load_env_vars() -> dict[str, str]:
    """Читает переменные окружения с префиксом TG_EXPORTER_ (ключи в lowercase)."""
    result: dict[str, str] = {}
    prefix_lower = _ENV_PREFIX.lower()
    for full_key, value in os.environ.items():
        lower_key = full_key.lower()
        if lower_key.startswith(prefix_lower):
            short_key = lower_key[len(prefix_lower):]
            result[short_key] = value
    return result


def build_merged_config(config_dir: Path) -> dict:
    """Собирает единый словарь конфигурации из всех источников.

    Порядок источников (последующий переопределяет предыдущий):
    1. Code defaults
    2. config.json (config_dir / "config.json")
    3. state.json (config_dir / "state.json", если есть)
    4. secrets.json (config_dir / "secrets.json", если есть)
    5. .env файл (config_dir / ".env")
    6. Env vars (os.environ, с префиксом TG_EXPORTER_)

    Правило: пустое значение (None, "") НЕ переопределяет непустое.
    """
    merged: dict = {}

    # 2. config.json
    _merge_dicts(merged, _load_json(config_dir / "config.json"))

    # 3. state.json
    _merge_dicts(merged, _load_json(config_dir / "state.json"))

    # 4. secrets.json
    _merge_dicts(merged, _load_json(config_dir / "secrets.json"))

    # 5. .env
    _merge_dicts(merged, _load_dotenv(config_dir / ".env"))

    # 6. Env vars (сильнейший приоритет)
    _merge_dicts(merged, _load_env_vars())

    return merged


class ConfigurationProvider:
    """Собирает конфигурацию из всех источников.
    Возвращает ConfigurationResult с сырым словарём — маппинг в типы делает хост.
    """

    def __init__(self, config_dir: Path) -> None:
        self._config_dir = config_dir

    def build(self) -> ConfigurationResult:
        merged = build_merged_config(self._config_dir)
        return ConfigurationResult(
            raw=merged,
            config_dir=self._config_dir,
        )


@dataclass(frozen=True)
class ConfigurationResult:
    """Сырой результат сборки конфигурации из всех источников.
    Хост маппит raw в типизированные конфиги при _bind_services.
    Регистрируется в DI как singleton — любой компонент может получить
    доступ к config_dir или сырым данным.
    """
    raw: dict          # объединённый словарь всех настроек
    config_dir: Path   # директория, где лежат config/state/secrets файлы
