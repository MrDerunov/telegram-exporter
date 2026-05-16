"""JsonSecretStore — хранилище секретов в secrets.json (для CI, права 0o600)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from tg_exporter.secrets.secret_store import ISecretStore
from tg_exporter.utils.file_utils import secure_permissions


class JsonSecretStore(ISecretStore):
    """Хранит секреты в secrets.json внутри config_dir."""

    def __init__(self, config_dir: Path) -> None:
        self._path = config_dir / "secrets.json"
        self._cache: dict[str, str] | None = None

    def _read(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        try:
            with self._path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            return {str(k): str(v) for k, v in raw.items() if isinstance(v, str)}
        except (json.JSONDecodeError, OSError):
            return {}

    def _load_cache(self) -> dict[str, str]:
        if self._cache is None:
            self._cache = self._read()
        return self._cache

    def get(self, key: str) -> str | None:
        return self._load_cache().get(key)

    def set(self, key: str, value: str) -> None:
        cache = self._load_cache()
        cache[key] = value
        self._write(cache)

    def delete(self, key: str) -> None:
        cache = self._load_cache()
        cache.pop(key, None)
        self._write(cache)

    def _write(self, data: dict[str, str]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, self._path)
        secure_permissions(self._path)
        self._cache = data
