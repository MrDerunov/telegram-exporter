"""Команда экспорта: базовый экспорт одного чата."""
from __future__ import annotations
import click
import asyncio
from pathlib import Path

from tg_exporter.services.export.export_task import ExportTask
from tg_exporter.services.export.export_format import ExportFormat
from tg_exporter.services.export.export_progress import ExportProgress
from tg_exporter.services.export.export_orchestrator import ExportOrchestrator
from tg_exporter.telegram.telegram_client_manager_interface import ITelegramClientManager
from tg_exporter.utils.cancellation import CancellationToken
from ..hosting import get_host


def _resolve_format(fmt: str) -> ExportFormat:
    mapping = {"json": ExportFormat.JSON, "markdown": ExportFormat.MARKDOWN, "both": ExportFormat.BOTH}
    return mapping.get(fmt, ExportFormat.BOTH)


def _chat_name(chat_id: str) -> str:
    """Безопасное имя директории из chat ID."""
    return str(chat_id).replace("/", "_").replace("\\", "_").replace("..", "_") or "export"


@click.group("export")
def export_group() -> None:
    """Экспорт сообщений из чатов."""
    pass


@export_group.command("run")
@click.option("--chat", required=True, help="ID или username чата/канала")
@click.option("--output", default=None, help="Директория для выгрузки")
@click.option("--format", "fmt", default="both", type=click.Choice(["json", "markdown", "both"]))
@click.option("--last", type=int, default=None, help="Экспортировать последние N сообщений")
def export_run(chat: str, output: str | None, fmt: str, last: int | None) -> None:
    """Базовый экспорт одного чата."""
    host = get_host()
    orchestrator = host.get(ExportOrchestrator)
    client_manager = host.get(ITelegramClientManager)

    export_format = _resolve_format(fmt)
    output_dir = Path(output) if output else Path.cwd() / "export" / _chat_name(chat)

    try:
        # Пытаемся преобразовать chat в int (peer_id)
        chat_id: int
        try:
            chat_id = int(chat)
        except ValueError:
            chat_id = 0  # username — потребует резолвинга

        task = ExportTask(
            chat_id=chat_id,
            chat_name=chat,
            output_path=str(output_dir),
            format=export_format,
            message_limit=last or 0,
        )

        token = CancellationToken()
        progress = ExportProgress()

        def _send(event_type: str, data: object) -> None:
            """Callback прогресса — выводит в консоль."""
            if event_type == "export_start":
                label, total = data
                click.echo(f"Начат экспорт: {label} ({'?' if total is None else total} сообщений)")
            elif event_type == "export_progress":
                current, total = data
                pct = f"{current}/{total}" if total else str(current)
                click.echo(f"\r  Обработано: {pct}", nl=False)
            elif event_type == "export_done":
                export_dir, files = data
                click.echo(f"\n✅ Экспорт завершён → {export_dir}")
                if files:
                    click.echo(f"  Файлы: {', '.join(files)}")
            elif event_type == "export_error":
                click.echo(f"\n❌ Ошибка: {data}")
            elif event_type == "export_cancelled":
                click.echo("\n⚠ Экспорт отменён")
            elif event_type == "export_status":
                if data:
                    click.echo(f"\n  {data}")
            elif event_type == "info":
                click.echo(f"\n  ℹ {data}")

        # Получаем диалог
        client = client_manager.create_client()
        loop = asyncio.get_event_loop() if asyncio.get_event_loop().is_running() else asyncio.new_event_loop()

        async def _get_dialog():
            await client.connect()
            dialogs = await client.get_dialogs()
            for d in dialogs:
                if str(d.id) == str(chat_id):
                    return d
                if getattr(d, "name", "") == chat or getattr(d, "title", "") == chat:
                    return d
            # Если диалог не найден — создаём минимальный объект для экспорта
            return _fallback_dialog(chat_id if chat_id else chat, chat)

        dialog = loop.run_until_complete(_get_dialog())

        orchestrator.run(dialog, task, token, progress, _send)

    except Exception as e:
        click.echo(f"❌ Ошибка экспорта: {e}", err=True)
        raise SystemExit(1)


def _fallback_dialog(peer_id, name: str):
    """Создаёт минимальный объект диалога, когда чат не найден в списке диалогов."""
    entity_type = type("Entity", (), {"id": peer_id, "title": name, "broadcast": True, "username": ""})()
    dialog_type = type("Dialog", (), {"id": peer_id, "name": name, "entity": entity_type, "title": name})()
    return dialog_type
