"""Фабрики для генерации тестовых данных с использованием Fake*-классов."""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any

from common.fakes.server.data_objects import (
    FakeUser,
    FakeChat,
    FakeFolder,
    FakeDialog,
    FakeMessage,
)
from .server import FakeTelegramServer


# ---------------------------------------------------------------------------
# FakeUser / FakeChat
# ---------------------------------------------------------------------------

def make_fake_user(
    id: int = 12345,
    first_name: str = "Test",
    last_name: str | None = "User",
    username: str = "test_user",
) -> FakeUser:
    """Создать фейкового пользователя."""
    return FakeUser(
        id=id,
        first_name=first_name,
        last_name=last_name,
        username=username,
    )


def make_fake_chat(
    id: int = -1001234,
    title: str = "Test Chat",
    broadcast: bool = False,
) -> FakeChat:
    """Создать фейковый чат/канал."""
    return FakeChat(id=id, title=title, broadcast=broadcast)


# ---------------------------------------------------------------------------
# FakeMessage
# ---------------------------------------------------------------------------

def make_fake_message(
    msg_id: int = 1,
    text: str = "Test message",
    date: datetime | None = None,
    sender: FakeUser | None = None,
    sender_id: int | None = 12345,
    **kwargs: Any,
) -> FakeMessage:
    """Создать одно фейковое сообщение."""
    if date is None:
        date = datetime.now(timezone.utc)
    return FakeMessage(
        id=msg_id,
        date=date,
        message=text,
        raw_text=text,
        sender=sender,
        sender_id=sender_id,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# FakeDialog
# ---------------------------------------------------------------------------

def make_fake_dialog(
    dialog_id: int = -1001234,
    name: str = "Test Chat",
    title: str = "Test Chat",
    entity: FakeUser | FakeChat | None = None,
    is_channel: bool = False,
    is_group: bool = False,
    is_user: bool = False,
    folder: str | None = None,
) -> FakeDialog:
    """Создать фейковый диалог."""
    if entity is None:
        entity = make_fake_chat(id=dialog_id, title=name)
    folder_obj = FakeFolder(title=folder) if folder else None
    return FakeDialog(
        id=dialog_id,
        name=name,
        title=title,
        entity=entity,
        is_channel=is_channel,
        is_group=is_group,
        is_user=is_user,
        folder=folder_obj,
    )


# ---------------------------------------------------------------------------
# Генераторы
# ---------------------------------------------------------------------------

def generate_messages(
    count: int,
    start_id: int = 1,
    peer_id: int = -1001234,
    sender: FakeUser | None = None,
) -> list[FakeMessage]:
    """Сгенерировать список фейковых сообщений."""
    now = datetime.now(timezone.utc)
    messages: list[FakeMessage] = []
    for i in range(count):
        msg_id = start_id + i
        msg = FakeMessage(
            id=msg_id,
            date=now - timedelta(hours=i),
            message=f"Test message #{msg_id}",
            raw_text=f"Test message #{msg_id}",
            sender_id=sender.id if sender else 12345,
            sender=sender,
        )
        messages.append(msg)
    return messages


def seed_server(
    server: FakeTelegramServer,
    users: list[FakeUser] | None = None,
    dialogs: list[FakeDialog] | None = None,
    messages: dict[int, list[FakeMessage]] | None = None,
    authorized: bool = True,
) -> None:
    """Заполнить сервер тестовыми данными одним вызовом."""
    if users:
        for u in users:
            server.users.add_user(u)
    if dialogs:
        for d in dialogs:
            server.dialogs.add_dialog(d)
    if messages:
        for peer_id, msgs in messages.items():
            server.messages.add_messages(peer_id, msgs)
    server.auth.set_authorized(authorized)


# ---------------------------------------------------------------------------
# ExportMessage (без изменений — не зависит от Fake*-классов)
# ---------------------------------------------------------------------------

def make_export_message(
    msg_id: int = 1,
    text: str = "Test message",
    date: datetime | None = None,
    from_name: str | None = "Test User",
    from_username: str | None = "test_user",
) -> Any:
    """Создать ExportMessage для тестов."""
    from tg_exporter.services.export.models.export_message import ExportMessage
    date_str = (date or datetime.now(timezone.utc)).isoformat()
    return ExportMessage(
        id=msg_id,
        type="message",
        date=date_str,
        from_name=from_name,
        from_username=from_username,
        text=text,
    )


# ---------------------------------------------------------------------------
# Совместимость: старые имена
# ---------------------------------------------------------------------------

# Старые функции, возвращавшие type()-объекты, больше не нужны.
# Оставлены make_dialog и generate_messages как ссылки на новые функции
# для обратной совместимости импортов.

def make_dialog(
    dialog_id: int = -1001234,
    name: str = "Test Chat",
    dialog_type: str = "channel",
    folder: str | None = None,
) -> Any:
    """Создать тестовый диалог (обратная совместимость).

    Deprecated: используйте make_fake_dialog.
    """
    return make_fake_dialog(
        dialog_id=dialog_id,
        name=name,
        title=name,
        is_channel=(dialog_type == "channel"),
        is_group=(dialog_type == "group"),
        is_user=(dialog_type == "user"),
        folder=folder,
    )
