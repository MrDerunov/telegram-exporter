"""JsonSettingsStore — хранилище состояния в state.json (атомарная запись + права 0o600)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from tg_exporter.configs.settings_store import ISettingsStore
from tg_exporter.configs.state_model import StateModel
from tg_exporter.utils.file_utils import secure_permissions
from tg_exporter.utils.logger import logger


class JsonSettingsStore(ISettingsStore):
    """Сохраняет StateModel в state.json внутри config_dir."""

    def __init__(self, config_dir: Path) -> None:
        self._path = config_dir / "state.json"

    def load(self) -> StateModel:
        if not self._path.exists():
            return StateModel()
        try:
            with self._path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            return StateModel.from_dict(raw)
        except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
            logger.warning(f"state.json: load failed: {exc}")
            return StateModel()

    def save(self, state: StateModel) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = state.to_dict()
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
