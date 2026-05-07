"""Утилита безопасного имени файла для экспортёров."""

import re


_WIN_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def sanitize_filename(name: str, max_len: int = 120) -> str:
    """
    Безопасное имя файла: запрещённые символы, control chars, обход через ..,
    Windows-зарезервированные имена, длина.
    """
    if not isinstance(name, str):
        name = str(name) if name is not None else ""
    cleaned = re.sub(r'[\x00-\x1f\x7f\\/:*?"<>|]+', "_", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.replace("..", "_")
    cleaned = cleaned.strip(". ")
    if cleaned.split(".", 1)[0].upper() in _WIN_RESERVED:
        cleaned = "_" + cleaned
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip("_ .")
    return cleaned or "chat_export"
