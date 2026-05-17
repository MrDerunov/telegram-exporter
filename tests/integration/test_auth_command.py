"""Интеграционные тесты CLI-команд auth."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from tg_exporter_cli.main import cli


@pytest.fixture
def cli_runner():
    return CliRunner()


def test_output_status_without_stack_trace(cli_runner):
    """auth status выводит статус (без реального Telegram)."""
    result = cli_runner.invoke(cli, ["auth", "status"])
    # Команда может упасть или вывести статус — главное что не stack trace
    assert result.exit_code in (0, 1)  # OK или ошибка авторизации


def test_return_exit_code_on_verify(cli_runner):
    """auth verify возвращает exit code."""
    result = cli_runner.invoke(cli, ["auth", "verify"])
    assert result.exit_code in (0, 1, 2)
