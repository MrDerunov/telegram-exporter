"""tg-exporter — консольная утилита для экспорта чатов Telegram."""
from __future__ import annotations
import click

from .container import Container


@click.group()
@click.version_option(version="1.0.0", prog_name="tg-exporter")
def cli() -> None:
    """tg-exporter — экспорт чатов Telegram в JSON и Markdown."""
    pass


@cli.group()
def auth() -> None:
    """Аутентификация в Telegram."""
    pass


@auth.command("login")
def auth_login() -> None:
    """Интерактивный вход в аккаунт."""
    click.echo("[TODO] auth login")


@auth.command("status")
def auth_status() -> None:
    """Проверить статус авторизации."""
    click.echo("[TODO] auth status")


@auth.command("logout")
def auth_logout() -> None:
    """Выйти из аккаунта."""
    click.echo("[TODO] auth logout")


@auth.command("export-session")
def auth_export_session() -> None:
    """Экспортировать сессию в secrets.env."""
    click.echo("[TODO] auth export-session")


@auth.command("verify")
def auth_verify() -> None:
    """Проверить валидность сессии (для CI/CD)."""
    click.echo("[TODO] auth verify")


@cli.group()
def export() -> None:
    """Экспорт сообщений из чатов."""
    pass


@export.command("run")
@click.option("--chat", required=True, help="ID или username чата")
def export_run(chat: str) -> None:
    """Запустить экспорт."""
    click.echo(f"[TODO] export --chat {chat}")


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


@cli.command("version")
def version() -> None:
    """Показать версию утилиты."""
    click.echo("tg-exporter 1.0.0")


@cli.command("doctor")
def doctor() -> None:
    """Диагностика окружения."""
    click.echo("[TODO] doctor")


if __name__ == "__main__":
    cli()
