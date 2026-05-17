"""Базовый класс для интеграционных тестов CLI-команд.

Предоставляет CliRunner и CliHost, настроенный с фейковыми зависимостями.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from tg_exporter_cli.main import cli
from tg_exporter_cli.hosting import CliHost
from tg_exporter.services.telegram import ITelegramClientManager
from tests.common.fakes import FakeTelegramClient, FakeTelegramClientManager


class TestCliCommandBase:
    """Базовый класс для тестов CLI-команд."""

    @pytest.fixture(autouse=True)
    def _setup_cli(self):
        self.runner = CliRunner()

    @staticmethod
    def _build_host(
        fake_client: FakeTelegramClient | None = None,
        authorized: bool = True,
    ) -> CliHost:
        """Создаёт CliHost с фейковым клиентом."""
        client = fake_client or FakeTelegramClient()
        client.set_authorized(authorized)
        manager = FakeTelegramClientManager(client)

        return (
            CliHost()
            .build()
            .rebind_services(lambda c, result: c.register_instance(ITelegramClientManager, manager))
        )

    def invoke(self, *args: str) -> object:
        """Запускает CLI-команду и возвращает результат."""
        return self.runner.invoke(cli, list(args))
