"""Команды управления профилями: list, add, remove, switch."""
from __future__ import annotations
import click

from tg_exporter.telegram.profiles.profile_manager import ProfileManager
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
        profiles = profile_manager.list()
        active_phone = profile_manager.active_phone()

        if not profiles:
            click.echo("Нет сохранённых профилей. Добавьте через: tg-exporter profile add")
            return

        click.echo(f"{'Телефон':<20} {'Имя':<20} {'API ID':<12} {'Статус'}")
        click.echo("-" * 70)
        for p in profiles:
            status = "▶ активный" if p.phone == active_phone else ""
            click.echo(f"{p.phone:<20} {p.display_name:<20} {p.api_id:<12} {status}")

    except Exception as e:
        click.echo(f"❌ Ошибка: {e}", err=True)
        raise SystemExit(1) from e


@profile_group.command("add")
@click.option("--phone", required=True, help="Номер телефона (+7999...)")
@click.option("--api-id", required=True, help="Telegram API ID")
@click.option("--api-hash", required=True, help="Telegram API Hash")
@click.option("--name", default=None, help="Отображаемое имя профиля")
def profile_add(phone: str, api_id: str, api_hash: str, name: str | None):
    """Добавить новый профиль."""
    host = get_host()
    profile_manager = host.get(ProfileManager)

    try:
        # api_hash сохраняется через ISecretStore (уже при auth login),
        # здесь только регистрируем профиль без сессии
        profile_manager.add_or_update(phone, api_id, "", display_name=name or phone, set_active=True)
        click.echo(f"✅ Профиль {phone} добавлен. Выполните auth login для входа.")

    except Exception as e:
        click.echo(f"❌ Ошибка добавления профиля: {e}", err=True)
        raise SystemExit(1) from e


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
        raise SystemExit(1) from e


@profile_group.command("switch")
@click.option("--phone", required=True, help="Номер телефона профиля")
def profile_switch(phone: str):
    """Переключить активный профиль."""
    host = get_host()
    profile_manager = host.get(ProfileManager)

    try:
        profile = profile_manager.set_active(phone)
        if profile is None:
            click.echo(f"❌ Профиль {phone} не найден.", err=True)
            raise SystemExit(1)

        click.echo(f"✅ Переключено на профиль {phone}")
    except Exception as e:
        click.echo(f"❌ Ошибка переключения: {e}", err=True)
        raise SystemExit(1) from e
