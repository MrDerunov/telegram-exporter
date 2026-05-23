"""tg-exporter — консольная утилита для экспорта чатов Telegram."""
from __future__ import annotations
import click

from tg_exporter_cli.cli_constants import VERSION
from tg_exporter_cli.commands.auth import auth_group
from tg_exporter_cli.commands.export import export_command
from tg_exporter_cli.commands.chat import chat_group
from tg_exporter_cli.commands.config_cmd import config_group
from tg_exporter_cli.commands.version import version_command
from tg_exporter_cli.commands.doctor import doctor_command


@click.group()
@click.version_option(version=VERSION, prog_name="tg-exporter")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """tg-exporter — экспорт чатов Telegram в JSON и Markdown."""
    if ctx.obj is None:
        from tg_exporter_cli.hosting import CliHost
        ctx.obj = CliHost().build()
    ctx.obj.run()


# Все команды
cli.add_command(auth_group)
cli.add_command(export_command)
cli.add_command(chat_group)
cli.add_command(config_group)
cli.add_command(version_command)
cli.add_command(doctor_command)


if __name__ == "__main__":
    cli()
