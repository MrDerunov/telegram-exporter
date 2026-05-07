"""Фикстуры для тестов tg-exporter."""
from __future__ import annotations
import pytest
from pathlib import Path

from tg_exporter_cli.container import Container
from tests.fakes.fake_telegram_client import FakeTelegramClient


@pytest.fixture
def fake_client() -> FakeTelegramClient:
    """Фейковый Telegram-клиент."""
    return FakeTelegramClient()


@pytest.fixture
def container_with_fake_client(fake_client: FakeTelegramClient, tmp_path: Path) -> Container:
    """Контейнер с фейковым клиентом."""
    config_path = tmp_path / "cli_config.yaml"
    env_file = tmp_path / ".env"
    return Container(
        config_path=config_path,
        env_file=env_file,
        telegram_client=fake_client,
    )
