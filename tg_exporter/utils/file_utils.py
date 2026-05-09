"""Файловые утилиты: права доступа и атомарная запись."""
from __future__ import annotations

import os
from pathlib import Path


def secure_permissions(path: Path, mode: int = 0o600) -> None:
    """Устанавливает безопасные права на файл/директорию.

    На Windows — no-op (там своя ACL-модель).
    На Unix — chmod(mode).
    """
    import platform
    if platform.system() == "Windows":
        return
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    """Атомарная запись файла: tmp → fsync → os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp_path, path)
    secure_permissions(path, mode)
