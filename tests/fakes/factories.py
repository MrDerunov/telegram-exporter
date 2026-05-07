"""Фабрики для генерации тестовых данных."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any
import random


def make_export_message(
    msg_id: int = 1,
    text: str = "Test message",
    date: datetime | None = None,
    from_name: str | None = "Test User",
    from_username: str | None = "test_user",
) -> Any:
    """Создать ExportMessage для тестов."""
    from tg_exporter.services.export.export_message import ExportMessage
    date_str = (date or datetime.now(timezone.utc)).isoformat()
    return ExportMessage(
        id=msg_id,
        type="message",
        date=date_str,
        from_name=from_name,
        from_username=from_username,
        text=text,
    )


def generate_messages(count: int, start_id: int = 1, peer_id: int = -1001234) -> list[Any]:
    """Сгенерировать список тестовых сообщений."""
    messages = []
    now = datetime.now(timezone.utc)
    for i in range(count):
        msg = type("Message", (), {
            "id": start_id + i,
            "date": now - timedelta(hours=i),
            "message": f"Test message #{start_id + i}",
            "sender_id": 12345,
            "peer_id": type("Peer", (), {"channel_id": -peer_id})(),
            "photo": None,
            "video": None,
            "voice": None,
            "document": None,
            "media": None,
            "reply_to": None,
            "reactions": None,
            "forwards": 0,
            "views": 100,
            "pinned": False,
            "mentioned": False,
        })()
        messages.append(msg)
    return messages


def make_dialog(
    dialog_id: int = -1001234,
    name: str = "Test Chat",
    dialog_type: str = "channel",
    folder: str | None = None,
) -> Any:
    """Создать тестовый диалог."""
    return type("Dialog", (), {
        "id": dialog_id,
        "name": name,
        "type": dialog_type,
        "folder": folder,
    })()
