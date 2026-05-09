"""Команда экспорта: полный экспорт одного чата или всех чатов из конфига."""
from __future__ import annotations
import click
import asyncio
import datetime
from pathlib import Path

from tg_exporter.services.export.export_task import ExportTask
from tg_exporter.services.export.export_format import ExportFormat
from tg_exporter.services.export.export_progress import ExportProgress
from tg_exporter.services.export.export_orchestrator import ExportOrchestrator
from tg_exporter.services.export_history import ExportHistory
from tg_exporter.telegram.telegram_client_manager_interface import ITelegramClientManager
from tg_exporter.utils.cancellation import CancellationToken
from tg_exporter_cli.hosting.cli_config import CliConfig
from ..hosting import get_host


def _resolve_format(fmt: str) -> ExportFormat:
    mapping = {"json": ExportFormat.JSON, "markdown": ExportFormat.MARKDOWN, "both": ExportFormat.BOTH}
    return mapping.get(fmt, ExportFormat.BOTH)


def _chat_name(chat_id: str) -> str:
    """Безопасное имя директории из chat ID."""
    return str(chat_id).replace("/", "_").replace("\\", "_").replace("..", "_") or "export"


def _parse_date(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        raise click.BadParameter(f"Неверный формат даты: {value}. Используйте YYYY-MM-DD.")


def _validate_flags(date_from, date_to, days, last):
    """Валидация конфликтующих флагов."""
    has_date = date_from or date_to
    if days and has_date:
        raise click.UsageError("--days нельзя комбинировать с --date-from/--date-to")
    if last and (has_date or days):
        raise click.UsageError("--last нельзя комбинировать с фильтрами по дате (--date-from, --date-to, --days)")


@click.group("export")
def export_group() -> None:
    """Экспорт сообщений из чатов."""
    pass


@export_group.command("run")
@click.option("--chat", default=None, help="ID или username чата/канала")
@click.option("--output", default=None, help="Директория для выгрузки")
@click.option("--format", "fmt", default="both", type=click.Choice(["json", "markdown", "both"]))
@click.option("--last", type=int, default=None, help="Экспортировать последние N сообщений")
@click.option("--date-from", default=None, help="Начало периода (YYYY-MM-DD)")
@click.option("--date-to", default=None, help="Конец периода (YYYY-MM-DD)")
@click.option("--days", type=int, default=None, help="Последние N дней (вместо date-from/date-to)")
@click.option("--topic-id", type=int, default=None, help="ID топика (для форумов)")
@click.option("--download-media", is_flag=True, help="Скачивать медиафайлы")
@click.option("--transcribe", is_flag=True, help="Транскрибировать голосовые")
@click.option("--transcriber", type=click.Choice(["local", "deepgram"]), default="local", help="Провайдер транскрипции")
@click.option("--analytics", is_flag=True, help="Собирать аналитику (top_authors.md, activity.md)")
@click.option("--words-per-file", type=int, default=None, help="Слов на Markdown-файл")
@click.option("--profile", default="default", help="Имя профиля")
@click.option("--resume", is_flag=True, help="Продолжить прерванный экспорт")
@click.option("--all", "export_all", is_flag=True, help="Экспортировать все чаты из конфига")
@click.option("--skip-unavailable", is_flag=True, help="Пропускать недоступные чаты (с --all)")
def export_run(
    chat: str | None,
    output: str | None,
    fmt: str,
    last: int | None,
    date_from: str | None,
    date_to: str | None,
    days: int | None,
    topic_id: int | None,
    download_media: bool,
    transcribe: bool,
    transcriber: str,
    analytics: bool,
    words_per_file: int | None,
    profile: str,
    resume: bool,
    export_all: bool,
    skip_unavailable: bool,
) -> None:
    """Экспорт сообщений из чата (или всех чатов с --all)."""
    host = get_host()
    orchestrator = host.get(ExportOrchestrator)
    client_manager = host.get(ITelegramClientManager)
    config = host.get(CliConfig)
    history = host.get(ExportHistory)

    # Валидация флагов
    date_from_dt = _parse_date(date_from)
    date_to_dt = _parse_date(date_to)
    _validate_flags(date_from_dt, date_to_dt, days, last)

    if days and not date_from_dt:
        date_from_dt = datetime.datetime.now() - datetime.timedelta(days=days)

    if transcribe and not download_media:
        click.echo("⚠ --transcribe без --download-media: транскрипция требует скачивания аудио.", err=True)

    export_format = _resolve_format(fmt)

    # Режим --all: экспорт всех чатов из конфига
    if export_all:
        chats = config.chats
        if not chats:
            click.echo("❌ Нет чатов в конфиге. Добавьте через: tg-exporter chats add --chat ID", err=True)
            raise SystemExit(1)
        for entry in chats:
            click.echo(f"\n📦 Экспорт: {entry.name} (ID: {entry.id})")
            try:
                _run_export(
                    host=host,
                    orchestrator=orchestrator,
                    client_manager=client_manager,
                    history=history,
                    chat=str(entry.id),
                    output=output,
                    export_format=export_format,
                    last=last,
                    date_from_dt=date_from_dt,
                    date_to_dt=date_to_dt,
                    topic_id=topic_id,
                    download_media=download_media,
                    transcribe=transcribe,
                    transcriber=transcriber,
                    analytics=analytics,
                    words_per_file=words_per_file,
                    profile=profile,
                    resume=resume,
                )
            except SystemExit as e:
                if e.code != 0 and skip_unavailable:
                    click.echo(f"  ⚠ Пропущен (недоступен)")
                    continue
                raise
        return

    # Одиночный экспорт
    if not chat:
        raise click.UsageError("Укажите --chat ID или --all для экспорта всех чатов.")

    _run_export(
        host=host,
        orchestrator=orchestrator,
        client_manager=client_manager,
        history=history,
        chat=chat,
        output=output,
        export_format=export_format,
        last=last,
        date_from_dt=date_from_dt,
        date_to_dt=date_to_dt,
        topic_id=topic_id,
        download_media=download_media,
        transcribe=transcribe,
        transcriber=transcriber,
        analytics=analytics,
        words_per_file=words_per_file,
        profile=profile,
        resume=resume,
    )


def _run_export(
    *,
    host,
    orchestrator: ExportOrchestrator,
    client_manager: ITelegramClientManager,
    history: ExportHistory,
    chat: str,
    output: str | None,
    export_format: ExportFormat,
    last: int | None,
    date_from_dt: datetime.datetime | None,
    date_to_dt: datetime.datetime | None,
    topic_id: int | None,
    download_media: bool,
    transcribe: bool,
    transcriber: str,
    analytics: bool,
    words_per_file: int | None,
    profile: str,
    resume: bool,
) -> None:
    """Выполняет экспорт одного чата."""
    output_dir = Path(output) if output else Path.cwd() / "export" / _chat_name(chat)

    # Инкрементальный режим (--resume)
    incremental = False
    last_exported_id: int | None = None
    if resume and output_dir.exists():
        hist_data = history.load(output_dir)
        if hist_data and hist_data.get("last_message_id"):
            incremental = True
            last_exported_id = hist_data["last_message_id"]
            click.echo(f"📋 Продолжение экспорта с сообщения #{last_exported_id}")

    try:
        chat_id: int
        try:
            chat_id = int(chat)
        except ValueError:
            chat_id = 0

        task = ExportTask(
            chat_id=chat_id,
            chat_name=chat,
            output_path=str(output_dir),
            format=export_format,
            message_limit=last or 0,
            date_from=date_from_dt,
            date_to=date_to_dt,
            topic_id=topic_id,
            download_media=download_media,
            collect_analytics=analytics,
            transcribe_audio=transcribe,
            transcription_provider=transcriber,
            incremental=incremental,
            last_exported_id=last_exported_id,
            words_per_file=words_per_file or 50000,
        )

        token = CancellationToken()
        progress = ExportProgress()

        def _send(event_type: str, data: object) -> None:
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
            return _fallback_dialog(chat_id if chat_id else chat, chat)

        dialog = loop.run_until_complete(_get_dialog())

        orchestrator.run(dialog, task, token, progress, _send)

    except Exception as e:
        click.echo(f"❌ Ошибка экспорта: {e}", err=True)
        raise SystemExit(1)


def _fallback_dialog(peer_id, name: str):
    """Создаёт минимальный объект диалога, когда чат не найден."""
    entity_type = type("Entity", (), {"id": peer_id, "title": name, "broadcast": True, "username": ""})()
    dialog_type = type("Dialog", (), {"id": peer_id, "name": name, "entity": entity_type, "title": name})()
    return dialog_type
