"""Базовый класс для интеграционных тестов CLI-команд.

Предоставляет CliRunner и CliHost, настроенный с фейковыми зависимостями.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from tg_exporter_cli.main import cli
from tg_exporter_cli.hosting import CliHost
from tg_exporter.services.telegram import ITelegramClientManager
from tg_exporter.settings.secrets.secret_store import ISecretStore
from tg_exporter.settings.configs import ISettingsStore
from tests.common.fakes import (
    FakeTelegramClient,
    FakeTelegramClientManager,
    FakeTelegramServer,
    FakeUser,
    FakeSecretStore,
    FakeSettingsStore,
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
        self.client_manager = FakeTelegramClientManager(self.client)

        self.fake_secrets = FakeSecretStore()
        self.fake_settings = FakeSettingsStore()

        self.host = (
            CliHost()
            .rebind_services(lambda c, r: c.register_instance(ITelegramClientManager, self.client_manager))
            .rebind_services(lambda c, r: c.register_instance(ISecretStore, self.fake_secrets))
            .rebind_services(lambda c, r: c.register_instance(ISettingsStore, self.fake_settings))
            .build()
        )

    def _invoke(self, *args: str, **kwargs):
        """Вызвать CLI-команду, передав host как Click context obj."""
        return self.runner.invoke(cli, list(args), obj=self.host, **kwargs)
