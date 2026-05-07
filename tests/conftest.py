"""Фикстуры для тестов tg-exporter."""
from __future__ import annotations
import pytest
from pathlib import Path

from tg_exporter_cli.hosting import CliHost
from tg_exporter.telegram.telegram_client_manager_interface import ITelegramClientManager
from tests.fakes.fake_telegram_client import FakeTelegramClient
from tests.fakes.fake_telegram_client_manager import FakeTelegramClientManager


@pytest.fixture
def fake_client() -> FakeTelegramClient:
    """Фейковый Telegram-клиент."""
    return FakeTelegramClient()


@pytest.fixture
def fake_manager(fake_client: FakeTelegramClient) -> FakeTelegramClientManager:
    """Фейковый менеджер клиентов."""
    return FakeTelegramClientManager(fake_client)


@pytest.fixture
def host_with_fake_client(fake_manager: FakeTelegramClientManager, tmp_path: Path) -> CliHost:
    """Хост с фейковым менеджером."""
    config_path = tmp_path / "cli_config.yaml"
    env_file = tmp_path / ".env"
    return (
        CliHost(config_path=config_path, env_file=env_file)
        .build()
        .rebind_services(lambda c: c.register_instance(ITelegramClientManager, fake_manager))
    )
