"""Команда экспорта: полный экспорт одного чата или всех чатов из конфига."""
from __future__ import annotations
import click
import datetime
from pathlib import Path

from tg_exporter.services.export.models.export_task import ExportTask
from tg_exporter.services.export.models.export_format import ExportFormat
from tg_exporter.services.export.models.export_progress import ExportProgress
from tg_exporter.services.export.export_orchestrator import ExportOrchestrator
from tg_exporter.services.export.export_history import ExportHistory
from tg_exporter.services.telegram import ITelegramClientManager
from tg_exporter.utils.cancellation import CancellationToken
from tg_exporter.settings.configs import StateModel
from tg_exporter_cli.utils.async_runner import run_async
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
        dt = datetime.datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.UTC)
        return dt
    except ValueError as e:
        raise click.BadParameter(f"Неверный формат даты: {value}. Используйте YYYY-MM-DD.") from e


def _validate_flags(date_from, date_to, days, last):
    """Валидация конфликтующих флагов."""
    has_date = date_from or date_to
    if days and has_date:
        raise click.UsageError("--days нельзя комбинировать с --date-from/--date-to")
    if last and (has_date or days):
        raise click.UsageError("--last нельзя комбинировать с фильтрами по дате (--date-from, --date-to, --days)")


@click.command("export")
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
@click.option("--resume", is_flag=True, help="Продолжить прерванный экспорт")
@click.option("--deduplicate", is_flag=True, help="Пропускать уже экспортированные сообщения")
@click.option("--all", "export_all", is_flag=True, help="Экспортировать все чаты из конфига")
@click.option("--skip-unavailable", is_flag=True, help="Пропускать недоступные чаты (с --all)")
def export_command(
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
    resume: bool,
    deduplicate: bool,
    export_all: bool,
    skip_unavailable: bool,
) -> None:
    """Экспорт сообщений из чатов."""
    host = get_host()
    orchestrator = host.get(ExportOrchestrator)
    client_manager = host.get(ITelegramClientManager)
    state = host.get(StateModel)
    history = host.get(ExportHistory)

    # Валидация флагов
    date_from_dt = _parse_date(date_from)
    date_to_dt = _parse_date(date_to)
    _validate_flags(date_from_dt, date_to_dt, days, last)

    # --last 0 = без ограничений
    if last is not None and last <= 0:
        last = None

    if days and not date_from_dt:
        date_from_dt = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days)

    if transcribe and not download_media:
        click.echo("⚠ --transcribe без --download-media: транскрипция требует скачивания аудио.", err=True)

    export_format = _resolve_format(fmt)

    # Режим --all: экспорт всех чатов из конфига
    if export_all:
        chats = state.chats
        if not chats:
            click.echo("❌ Нет чатов в конфиге. Добавьте через: tg-exporter chat add --chat ID", err=True)
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
                    resume=resume,
                    deduplicate=deduplicate,
                )
            except SystemExit as e:
                if e.code != 0 and skip_unavailable:
                    click.echo(f"  ⚠ Ошибка экспорта {entry.name}, пропускаю.")
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
        resume=resume,
        deduplicate=deduplicate,
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
    resume: bool,
    deduplicate: bool,
) -> None:
    """Выполняет экспорт одного чата."""
    output_dir = Path(output) if output else Path.cwd() / "export" / _chat_name(chat)

    # Инкрементальный режим (--resume) или дедупликация (--deduplicate)
    incremental = False
    last_exported_id: int | None = None
    if resume and output_dir.exists():
        hist_data = history.load(output_dir)
        if hist_data and hist_data.last_message_id:
            incremental = True
            last_exported_id = hist_data.last_message_id
            click.echo(f"📋 Продолжение экспорта с сообщения #{last_exported_id}")
    elif deduplicate:
        hist_data = history.load(output_dir)
        if hist_data and hist_data.last_message_id:
            last_exported_id = hist_data.last_message_id
            click.echo(f"🔍 Дедупликация: пропуск сообщений до #{last_exported_id}")

    try:
        # Определяем chat_id: int для peer_id, str для username
        chat_id: int | None = None
        try:
            chat_id = int(chat)
        except ValueError:
            chat_id = None  # username — потребует резолвинга

        task = ExportTask(
            output_path=str(output_dir),
            format=export_format,
            message_limit=last,
            date_from=date_from_dt,
            date_to=date_to_dt,
            topic_id=topic_id,
            download_media=download_media,
            collect_analytics=analytics,
            transcribe_audio=transcribe,
            transcription_provider=transcriber,
            incremental=incremental,
            last_exported_id=last_exported_id,
            deduplicate=deduplicate,
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

        # Получаем диалог
        async def _get_dialog():
            client = await client_manager.create_connected_client()
            dialogs = await client.get_dialogs()
            # Поиск по точному ID или username
            if chat_id is not None:
                target_id = str(chat_id)
                for d in dialogs:
                    if str(d.id) == target_id:
                        return d
            # Поиск по имени/username
            for d in dialogs:
                d_name = getattr(d, "name", "") or ""
                d_title = getattr(d, "title", "") or ""
                if d_name == chat or d_title == chat:
                    return d
                # Username может быть вида @channel
                entity = getattr(d, "entity", None)
                if entity and getattr(entity, "username", "") == chat.lstrip("@"):
                    return d
            return None

        dialog = run_async(_get_dialog())

        if dialog is None:
            click.echo(f"❌ Чат «{chat}» не найден. Проверьте ID или username.", err=True)
            raise SystemExit(1)

        run_async(orchestrator.run(dialog, task, token, progress, _send))

    except Exception as e:
        click.echo(f"❌ Ошибка экспорта: {e}", err=True)
        raise SystemExit(1) from e
