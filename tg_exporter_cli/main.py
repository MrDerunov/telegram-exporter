"""tg-exporter — консольная утилита для экспорта чатов Telegram."""
from __future__ import annotations
import click

from tg_exporter_cli.cli_constants import VERSION
from .commands.auth import auth_group
from .commands.export import export_group
from .commands.chats import chats_group
from .commands.profile import profile_group
from .commands.config_cmd import config_group
from .commands.version import version_command
from .commands.doctor import doctor_command


@click.group()
@click.version_option(version=VERSION, prog_name="tg-exporter")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """tg-exporter — экспорт чатов Telegram в JSON и Markdown."""
    from .hosting import CliHost

    ctx.obj = CliHost().build()
    ctx.obj.run()


# Все команды
cli.add_command(auth_group)
cli.add_command(export_group)
cli.add_command(chats_group)
cli.add_command(profile_group)
cli.add_command(config_group)
cli.add_command(version_command)
cli.add_command(doctor_command)


if __name__ == "__main__":
    cli()
