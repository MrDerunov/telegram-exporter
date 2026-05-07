"""tg-exporter — консольная утилита для экспорта чатов Telegram."""
from __future__ import annotations
import click

from .commands.auth import auth_group
from .commands.export import export_group
from .commands.version import version_command
from .commands.doctor import doctor_command


@click.group()
@click.version_option(version="1.0.0", prog_name="tg-exporter")
def cli() -> None:
    """tg-exporter — экспорт чатов Telegram в JSON и Markdown."""
    pass


# Реальные команды
cli.add_command(auth_group)
cli.add_command(export_group)
cli.add_command(version_command)
cli.add_command(doctor_command)


# Заглушки (будут реализованы в Фазе 3/4)
@cli.group()
def chats() -> None:
    """Управление списком чатов."""
    pass


@chats.command("list")
def chats_list() -> None:
    """Показать список чатов."""
    click.echo("[TODO] chats list")


@cli.group()
def profile() -> None:
    """Управление аккаунтами."""
    pass


@profile.command("list")
def profile_list() -> None:
    """Показать список аккаунтов."""
    click.echo("[TODO] profile list")


@cli.group()
def config() -> None:
    """Управление конфигурацией."""
    pass


@config.command("show")
def config_show() -> None:
    """Показать текущий конфиг."""
    click.echo("[TODO] config show")


if __name__ == "__main__":
    cli()
