"""
MediaDirs — пути к поддиректориям медиа внутри export_dir.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from tg_exporter.services.export.models.media_type import MediaType


@dataclass
class MediaDirs:
    """Пути к поддиректориям медиа внутри export_dir."""
    photo: str
    video: str
    audio: str
    documents: str

    @classmethod
    def create(cls, base: str) -> MediaDirs:
        dirs = cls(
            photo=os.path.join(base, "photo"),
            video=os.path.join(base, "video"),
            audio=os.path.join(base, "audio"),
            documents=os.path.join(base, "documents"),
        )
        for d in (dirs.photo, dirs.video, dirs.audio, dirs.documents):
            os.makedirs(d, exist_ok=True)
        return dirs

    def for_media_type(self, media_type: MediaType | None) -> str | None:
        if media_type == MediaType.PHOTO:
            return self.photo
        if media_type in (MediaType.VIDEO, MediaType.VIDEO_NOTE, MediaType.ANIMATION):
            return self.video
        if media_type in (MediaType.VOICE, MediaType.AUDIO):
            return self.audio
        if media_type == MediaType.DOCUMENT:
            return self.documents
        return None
