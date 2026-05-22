"""Базовый класс для интеграционных тестов CLI-команд.

Предоставляет CliRunner и CliHost, настроенный с фейковыми зависимостями.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from tg_exporter_cli.main import cli
from tg_exporter_cli.hosting import CliHost
from tg_exporter.services.telegram import ITelegramClientManager
from tests.common.fakes import (
    FakeTelegramClient,
    FakeTelegramClientManager,
    FakeTelegramServer,
    FakeUser,
)


class TestCliCommandBase:
    """Базовый класс для тестов CLI-команд.

    Создаёт host с фейковым клиентом перед каждым тестом.
    Доступны как self.host, self.server, self.client, self.test_user.
    По умолчанию сервер авторизован.
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.runner = CliRunner()
        self.server = FakeTelegramServer()
        self.server.auth.set_authorized(True)
        self.test_user = FakeUser(
            id=12345,
            first_name="Test",
            last_name="User",
            username="test_user",
        )
        self.server.users.add_user(self.test_user)
        self.client = FakeTelegramClient(self.server)
        manager = FakeTelegramClientManager(self.client)
        self.host = (
            CliHost()
            .build()
            .rebind_services(lambda c, result: c.register_instance(ITelegramClientManager, manager))
        )

    def _invoke(self, *args: str, **kwargs):
        """Вызвать CLI-команду, передав host как Click context obj."""
        return self.runner.invoke(cli, list(args), obj=self.host, **kwargs)
