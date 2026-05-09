"""Команды управления профилями: list, add, remove, switch."""
from __future__ import annotations
import click
import asyncio

from tg_exporter.telegram.telegram_client_manager_interface import ITelegramClientManager
from tg_exporter.telegram.profiles.profile_manager import ProfileManager
from tg_exporter_cli.hosting.cli_config import CliConfig
from tg_exporter_cli.hosting.cli_config_repository import save_cli_config
from ..hosting import get_host


@click.group("profile")
def profile_group():
    """Управление аккаунтами Telegram."""
    pass


@profile_group.command("list")
def profile_list():
    """Список профилей."""
    host = get_host()
    profile_manager = host.get(ProfileManager)

    try:
        profiles = profile_manager.get_all()
        active = profile_manager.get_active_phone()

        if not profiles:
            click.echo("Нет сохранённых профилей. Добавьте через: tg-exporter profile add")
            return

        click.echo(f"{'Телефон':<20} {'Имя':<20} {'API ID':<12} {'Статус'}")
        click.echo("-" * 70)
        for p in profiles:
            status = "▶ активный" if p.phone == active else ""
            click.echo(f"{p.phone:<20} {p.display_name:<20} {p.api_id:<12} {status}")

    except Exception as e:
        click.echo(f"❌ Ошибка: {e}", err=True)
        raise SystemExit(1)


@profile_group.command("add")
@click.option("--phone", required=True, help="Номер телефона (+7999...)")
@click.option("--api-id", required=True, help="Telegram API ID")
@click.option("--api-hash", required=True, help="Telegram API Hash")
@click.option("--name", default=None, help="Отображаемое имя профиля")
def profile_add(phone: str, api_id: str, api_hash: str, name: str | None):
    """Добавить новый профиль."""
    host = get_host()
    profile_manager = host.get(ProfileManager)
    config = host.get(CliConfig)

    try:
        profile_manager.add(phone, api_id, api_hash, name or phone)
        click.echo(f"✅ Профиль {phone} добавлен.")

        if not config.default_profile or config.default_profile == "default":
            config.default_profile = phone
            save_cli_config(config, host.config_path)

    except Exception as e:
        click.echo(f"❌ Ошибка добавления профиля: {e}", err=True)
        raise SystemExit(1)


@profile_group.command("remove")
@click.option("--phone", required=True, help="Номер телефона профиля")
def profile_remove(phone: str):
    """Удалить профиль."""
    host = get_host()
    profile_manager = host.get(ProfileManager)

    try:
        if profile_manager.remove(phone):
            click.echo(f"✅ Профиль {phone} удалён.")
        else:
            click.echo(f"❌ Профиль {phone} не найден.", err=True)
            raise SystemExit(1)
    except Exception as e:
        click.echo(f"❌ Ошибка: {e}", err=True)
        raise SystemExit(1)


@profile_group.command("switch")
@click.option("--phone", required=True, help="Номер телефона профиля")
def profile_switch(phone: str):
    """Переключить активный профиль."""
    host = get_host()
    profile_manager = host.get(ProfileManager)
    client_manager = host.get(ITelegramClientManager)

    try:
        profile = profile_manager.set_active(phone)
        if profile is None:
            click.echo(f"❌ Профиль {phone} не найден.", err=True)
            raise SystemExit(1)
        client_manager.destroy()
        client_manager.use_session(profile.session)
        click.echo(f"✅ Переключено на профиль {phone}")
    except Exception as e:
        click.echo(f"❌ Ошибка переключения: {e}", err=True)
        raise SystemExit(1)
