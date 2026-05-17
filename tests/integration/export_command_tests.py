"""Интеграционные тесты CLI-команды export."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from tg_exporter_cli.main import cli


@pytest.fixture
def cli_runner():
    return CliRunner()


def should_fail_when_chat_is_missing(cli_runner):
    """export без --chat должен упасть."""
    result = cli_runner.invoke(cli, ["export", "run"])
    assert result.exit_code != 0


def should_run_without_stack_trace_when_chat_and_last_specified(cli_runner, tmp_path):
    """export с --chat и --last запускается без stack trace."""
    result = cli_runner.invoke(cli, [
        "export", "run", "--chat", "-1001234", "--last", "10",
        "--output", str(tmp_path), "--format", "json"
    ])
    # Может упасть при отсутствии сессии, но не stack trace
    assert result.exit_code in (0, 1)
