"""AppConfigRepository — загрузка и сохранение AppConfig из/в JSON."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .app_config import AppConfig
from ..utils.file_utils import secure_permissions

CONFIG_DIR = Path(os.path.expanduser("~/.tg-exporter"))
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_app_config() -> AppConfig:
    """Загружает конфиг из файла. Возвращает дефолтный если файл не существует.

    При повреждении файла делает бэкап config.json.broken.{timestamp},
    чтобы пользователь мог восстановить настройки вручную, а не получал
    молчаливый сброс.
    """
    if not CONFIG_FILE.exists():
        return AppConfig()
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        raw.pop("api_hash", None)
        raw.pop("session", None)
        return AppConfig.from_dict(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        try:
            import datetime as _dt
            ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = CONFIG_FILE.with_suffix(f".broken.{ts}.json")
            CONFIG_FILE.rename(backup)
        except OSError:
            pass
        return AppConfig()


def save_app_config(config: AppConfig) -> None:
    """Сохраняет только несекретные поля. Атомарно + права 0o600."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = CONFIG_FILE.with_suffix(CONFIG_FILE.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp_path, CONFIG_FILE)
    secure_permissions(CONFIG_FILE)
