"""Сквозной сценарий: авторизация → экспорт на фейковом клиенте."""

from __future__ import annotations

import json
import os
from pathlib import Path

from tg_exporter_cli.hosting import CliHost
from tg_exporter_cli.async_runner import run_async
from tg_exporter.telegram.auth.auth_step import AuthStep
from tg_exporter.telegram.auth.auth_service import AuthService
from tg_exporter.telegram.telegram_client_manager_interface import ITelegramClientManager
from tg_exporter.services.export.export_orchestrator import ExportOrchestrator
from tests.fakes.fake_telegram_client import FakeTelegramClient
from tests.fakes.fake_telegram_client_manager import FakeTelegramClientManager
from tests.fakes.factories import generate_messages, make_export_message
from tg_exporter.services.export.export_task import ExportTask
from tg_exporter.services.export.export_format import ExportFormat
from tg_exporter.services.export.export_progress import ExportProgress
from tg_exporter.utils.cancellation import CancellationToken


def test_full_flow_auth_and_export(tmp_path: Path) -> None:
    """Полный цикл: проверка авторизации → экспорт через фейкового клиента."""
    # ---- Setup: фейковый клиент с авторизацией и сообщениями ----
    fake_client = FakeTelegramClient()
    fake_client.set_authorized(True)
    fake_client.add_messages(-1001234567890, generate_messages(100, peer_id=-1001234567890))

    fake_manager = FakeTelegramClientManager(fake_client)

    config_path = tmp_path / "cli_config.yaml"
    env_file = tmp_path / ".env"
    host = (
        CliHost(config_path=config_path, env_file=env_file)
        .build()
        .rebind_services(lambda c: c.register_instance(ITelegramClientManager, fake_manager))
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

    orchestrator.run(dialog, task, token, progress, collect_events)

    # ---- Проверка результата ----
    # Выводим события для отладки
    error_events = [e for e in events if e[0] == "export_error"]
    error_msg = error_events[0][1] if error_events else progress.error
    assert progress.status.name == "DONE", f"Expected DONE, got {progress.status.name}. Error: {error_msg}. Events: {[e[0] for e in events]}"
    assert len(progress.output_files) > 0

    # Ищем result.json в output_files
    json_files = [f for f in progress.output_files if f.endswith("result.json")]
    assert len(json_files) > 0, f"No result.json in {progress.output_files}"

    result_file = json_files[0]
    assert os.path.isfile(result_file)
    data = json.loads(Path(result_file).read_text())
    assert "messages" in data
    assert len(data["messages"]) > 0

    # Проверяем что был отправлен export_done
    done_events = [e for e in events if e[0] == "export_done"]
    assert len(done_events) == 1
