"""
MediaType — перечисление типов медиа-вложений Telegram.
"""

from __future__ import annotations

from enum import Enum


class MediaType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    AUDIO = "audio"
    VOICE = "voice"
    VIDEO_NOTE = "video_note"
    DOCUMENT = "document"
    STICKER = "sticker"
    ANIMATION = "animation"
