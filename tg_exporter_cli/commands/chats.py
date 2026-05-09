"""Команды управления чатами: list, show, add, remove."""
from __future__ import annotations
import click
import dataclasses

from tg_exporter.telegram.telegram_client_manager_interface import ITelegramClientManager
from tg_exporter_cli.hosting.cli_config import CliConfig, ChatEntry
from tg_exporter_cli.hosting.cli_config_repository import save_cli_config
from tg_exporter_cli.utils.async_runner import run_async
from ..hosting import get_host


@click.group("chats")
def chats_group():
    """Просмотр и управление чатами для экспорта."""
    pass


@chats_group.command("list")
@click.option("--folder", default=None, help="Показать чаты только в этой папке")
@click.option("--folders", "folders_only", is_flag=True, help="Показать только список папок")
@click.option("--search", default=None, help="Поиск по названию чата")
def chats_list(
        folder: str | None,
        folders_only: bool,
        search: str | None):
    """Список чатов из Telegram."""
    host = get_host()
    client_manager = host.get(ITelegramClientManager)

    try:
        client = client_manager.create_client()

        async def _fetch():
            await client.connect()
            return await client.get_dialogs()

        dialogs = run_async(_fetch())

        if folders_only:
            folders: set[str] = set()
            for d in dialogs:
                f = getattr(d, "folder", None)
                if f and getattr(f, "title", ""):
                    folders.add(f.title)
            if folders:
                click.echo("📁 Папки Telegram:")
                for f in sorted(folders):
                    click.echo(f"  {f}")
            else:
                click.echo("📁 Папок не найдено.")
            return

        results = []
        for d in dialogs:
            name = getattr(d, "name", "") or getattr(d, "title", "") or str(d.id)
            if search and search.lower() not in name.lower():
                continue
            if folder:
                f = getattr(d, "folder", None)
                f_title = getattr(f, "title", "") if f else ""
                if f_title.lower() != folder.lower():
                    continue
            d_type = _dialog_type(d)
            d_folder = getattr(getattr(d, "folder", None), "title", "—") or "—"
            results.append((d.id, name, d_type, d_folder))

        if not results:
            msg = f"Чаты не найдены{f' по запросу «{search}»' if search else ''}{f' в папке «{folder}»' if folder else ''}."
            click.echo(msg)
            return

        click.echo(f"{'ID':>12}  {'Название':<35} {'Тип':<10} Папка")
        click.echo("-" * 80)
        for chat_id, name, d_type, d_folder in results:
            short_name = name[:35] if len(name) <= 35 else name[:32] + "..."
            click.echo(f"{chat_id:>12}  {short_name:<35} {d_type:<10} {d_folder}")

    except Exception as e:
        click.echo(f"❌ Ошибка получения чатов: {e}", err=True)
        raise SystemExit(1)


@chats_group.command("show")
@click.option("--chat", "chat_id", required=True, help="ID чата")
def chats_show(chat_id: str):
    """Информация о конкретном чате."""
    host = get_host()
    client_manager = host.get(ITelegramClientManager)

    try:
        client = client_manager.create_client()

        async def _fetch():
            await client.connect()
            dialogs = await client.get_dialogs()
            for d in dialogs:
                if str(d.id) == chat_id:
                    return d
            return None

        dialog = run_async(_fetch())
        if dialog is None:
            click.echo(f"❌ Чат {chat_id} не найден.", err=True)
            raise SystemExit(1)

        name = getattr(dialog, "name", "") or getattr(dialog, "title", "") or str(dialog.id)
        d_type = _dialog_type(dialog)
        click.echo(f"Название: {name}")
        click.echo(f"ID:       {dialog.id}")
        click.echo(f"Тип:      {d_type}")
        if hasattr(dialog, "message") and dialog.message:
            click.echo(f"Последнее сообщение: {getattr(dialog.message, 'date', '—')}")

    except Exception as e:
        click.echo(f"❌ Ошибка: {e}", err=True)
        raise SystemExit(1)


@chats_group.command("add")
@click.option("--chat", "chat_id", default=None, help="ID чата для добавления")
@click.option("--folder", default=None, help="Добавить все чаты из папки Telegram")
def chats_add(chat_id: str | None, folder: str | None):
    """Добавить чат(ы) в конфиг для быстрого доступа."""
    host = get_host()
    client_manager = host.get(ITelegramClientManager)
    config = host.get(CliConfig)
    config_path = host.config_path

    if not chat_id and not folder:
        raise click.UsageError("Укажите --chat ID или --folder NAME")

    try:
        client = client_manager.create_client()

        async def _fetch():
            await client.connect()
            return await client.get_dialogs()

        dialogs = run_async(_fetch())
        added = 0
        existing_ids = {c.id for c in config.chats}
        new_chats = list(config.chats)

        if chat_id:
            target_id = int(chat_id)
            for d in dialogs:
                if d.id == target_id:
                    name = getattr(d, "name", "") or getattr(d, "title", "") or str(d.id)
                    if target_id not in existing_ids:
                        new_chats.append(ChatEntry(name=name, id=target_id))
                        added = 1
                        click.echo(f"✅ Чат «{name}» (ID: {target_id}) добавлен в конфиг.")
                    else:
                        click.echo(f"⚠ Чат «{name}» уже в конфиге.")
                    break
            else:
                click.echo(f"❌ Чат {chat_id} не найден в диалогах.", err=True)
                raise SystemExit(1)

        elif folder:
            for d in dialogs:
                f = getattr(d, "folder", None)
                f_title = getattr(f, "title", "") if f else ""
                if f_title.lower() == folder.lower():
                    did = d.id
                    if did not in existing_ids:
                        name = getattr(d, "name", "") or getattr(d, "title", "") or str(did)
                        new_chats.append(ChatEntry(name=name, id=did))
                        existing_ids.add(did)
                        added += 1
            if added:
                click.echo(f"✅ {added} чатов из папки «{folder}» добавлено в конфиг.")
            else:
                click.echo(f"⚠ В папке «{folder}» не найдено новых чатов.")

        if added:
            config = dataclasses.replace(config, chats=tuple(new_chats))
            save_cli_config(config, config_path)

    except Exception as e:
        click.echo(f"❌ Ошибка: {e}", err=True)
        raise SystemExit(1)


@chats_group.command("remove")
@click.option("--chat", "chat_id", required=True, help="ID чата для удаления из конфига")
def chats_remove(chat_id: str):
    """Убрать чат из конфига."""
    host = get_host()
    config = host.get(CliConfig)
    config_path = host.config_path

    target_id = int(chat_id)
    for c in config.chats:
        if c.id == target_id:
            new_chats = tuple(ch for ch in config.chats if ch.id != target_id)
            config = dataclasses.replace(config, chats=new_chats)
            save_cli_config(config, config_path)
            click.echo(f"✅ Чат «{c.name}» (ID: {target_id}) удалён из конфига.")
            return

    click.echo(f"❌ Чат {chat_id} не найден в конфиге.", err=True)
    raise SystemExit(1)


def _dialog_type(dialog) -> str:
    """Определяет тип диалога."""
    if getattr(dialog, "is_user", False):
        return "user"
    if getattr(dialog, "is_group", False):
        return "group"
    if getattr(dialog, "is_channel", False):
        entity = getattr(dialog, "entity", None)
        if entity and getattr(entity, "broadcast", False):
            return "channel"
    return "chat"
