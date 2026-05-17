"""Сквозной сценарий: авторизация → экспорт на фейковом клиенте."""

from __future__ import annotations

import json
import os
from pathlib import Path

from tg_exporter_cli.hosting import CliHost
from tg_exporter_cli.utils.async_runner import run_async
from tg_exporter.services.auth import AuthStep
from tg_exporter.services.telegram import AuthService
from tg_exporter.services.telegram import ITelegramClientManager
from tg_exporter.services.export.export_orchestrator import ExportOrchestrator
from tests.common.fakes.fake_telegram_client import FakeTelegramClient
from tests.common.fakes import FakeTelegramClientManager
from tests.common.fakes.factories import generate_messages
from tg_exporter.services.export.models.export_task import ExportTask
from tg_exporter.services.export.models.export_format import ExportFormat
from tg_exporter.services.export.models.export_progress import ExportProgress
from tg_exporter.utils.cancellation import CancellationToken


def test_complete_full_flow_auth_and_export(tmp_path: Path) -> None:
    """Полный цикл: проверка авторизации → экспорт через фейкового клиента."""
    # ---- Setup: фейковый клиент с авторизацией и сообщениями ----
    fake_client = FakeTelegramClient()
    fake_client.set_authorized(True)
    fake_client.add_messages(-1001234567890, generate_messages(100, peer_id=-1001234567890))

    fake_manager = FakeTelegramClientManager(fake_client)

    host = (
        CliHost()
        .build()
        .rebind_services(lambda c, result: c.register_instance(ITelegramClientManager, fake_manager))
    )

    # ---- Шаг 1: проверка авторизации через сервис ----
    auth = host.get(AuthService)
    result = run_async(auth.check_session())
    assert result.step == AuthStep.SUCCESS, f"Expected SUCCESS, got {result.step}"

    # ---- Шаг 2: создание задачи экспорта ----
    chat_id = -1001234567890
    output_dir = tmp_path / "export" / "test_chat"
    task = ExportTask(
        chat_id=chat_id,
        chat_name="Test Chat",
        output_path=str(output_dir),
        format=ExportFormat.JSON,
        message_limit=20,
    )

    # ---- Шаг 3: создание диалога для оркестратора ----
    entity = type("Entity", (), {
        "id": chat_id,
        "title": "Test Chat",
        "broadcast": True,
        "username": "",
    })()
    dialog = type("Dialog", (), {
        "id": chat_id,
        "name": "Test Chat",
        "entity": entity,
        "title": "Test Chat",
    })()

    # ---- Шаг 4: запуск экспорта ----
    orchestrator = host.get(ExportOrchestrator)
    token = CancellationToken()
    progress = ExportProgress()

    events: list[tuple[str, object]] = []

    def collect_events(event_type: str, data: object) -> None:
        events.append((event_type, data))

    import asyncio
    asyncio.run(orchestrator.run(dialog, task, token, progress, collect_events))

    # ---- Проверка результата ----
    error_events = [e for e in events if e[0] == "export_error"]
    error_msg = error_events[0][1] if error_events else progress.error
    assert progress.status.name == "DONE", (
        f"Expected DONE, got {progress.status.name}. "
        f"Error: {error_msg}. Events: {[e[0] for e in events]}"
    )
    assert len(progress.output_files) > 0

    json_files = [f for f in progress.output_files if f.endswith("result.json")]
    assert len(json_files) > 0, f"No result.json in {progress.output_files}"

    result_file = json_files[0]
    assert os.path.isfile(result_file)
    data = json.loads(Path(result_file).read_text())
    assert "messages" in data
    assert len(data["messages"]) > 0

    done_events = [e for e in events if e[0] == "export_done"]
    assert len(done_events) == 1
