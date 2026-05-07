"""Фикстуры для тестов tg-exporter."""
from __future__ import annotations
import pytest
from pathlib import Path

from tg_exporter_cli.container import Container
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
def container_with_fake_client(fake_manager: FakeTelegramClientManager, tmp_path: Path) -> Container:
    """Контейнер с фейковым менеджером."""
    config_path = tmp_path / "cli_config.yaml"
    env_file = tmp_path / ".env"
    return Container(
        config_path=config_path,
        env_file=env_file,
        telegram_manager=fake_manager,
    )
