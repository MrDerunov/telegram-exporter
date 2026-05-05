"""
AudioPrepResult — результат подготовки аудио к транскрипции.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class AudioPrepResult:
    """Результат подготовки аудио к транскрипции."""
    audio_data: bytes
    content_type: str
    saved_path: Optional[str] = None  # путь куда сохранено (для video_note)
