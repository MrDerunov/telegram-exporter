"""Команды аутентификации: login, status, logout, export-session, verify."""
from __future__ import annotations
import click
from pathlib import Path

from ..hosting import get_host
from tg_exporter_cli.utils.async_runner import run_async
from tg_exporter_cli.cli_constants import DEFAULT_SECRETS_EXPORTED_ENV_FILENAME
from tg_exporter.services.telegram import AuthService, AuthResult, SendCodeParams, VerifyCodeParams, ExportSessionParams
from tg_exporter.services.telegram import ITelegramClientManager
from tg_exporter.secrets.secret_store import ISecretStore
from tg_exporter.secrets.secret_keys import API_HASH, API_ID, SESSION
from tg_exporter.configs.static_config import StaticConfig


@click.group("auth")
def auth_group():
    """Аутентификация в Telegram."""
    pass


@auth_group.command("login")
@click.option("--phone", help="Номер телефона (+7999...)")
@click.option("--api-id", help="Telegram API ID")
@click.option("--api-hash", help="Telegram API Hash")
@click.option("--profile", default="default", help="Имя профиля")
def auth_login(phone, api_id, api_hash, profile):
    """Интерактивный вход в аккаунт Telegram."""
    host = get_host()
    config = host.get(StaticConfig)
    secret_store = host.get(ISecretStore)
    auth_service = host.get(AuthService)
    client_manager = host.get(ITelegramClientManager)

    # API credentials
    if api_id:
        secret_store.set(API_ID, api_id)
    if api_hash:
        secret_store.set(API_HASH, api_hash)
    if not config.api_id:
        api_id = click.prompt("API ID")
        secret_store.set(API_ID, api_id)
    if not config.api_hash and not secret_store.get(API_HASH):
        api_hash = click.prompt("API Hash", hide_input=True)
        secret_store.set(API_HASH, api_hash)

    # Phone
    if not phone:
        phone = click.prompt("Номер телефона (+7999...)")

    # Send code
    result = run_async(auth_service.send_code(SendCodeParams(phone=phone)))
    if result.step.name == "ERROR":
        click.echo(f"❌ {result.error}", err=True)
        raise SystemExit(1)

    click.echo("📱 Код отправлен в Telegram")

    # Verify code
    code = click.prompt("Код из Telegram")
    result = run_async(auth_service.verify_code(
        VerifyCodeParams(phone=phone, phone_hash=result.phone_code_hash, code=code)
    ))

    if result.step.name == "PASSWORD_REQUIRED":
        password = click.prompt("Пароль 2FA", hide_input=True)
        result = run_async(auth_service.verify_password(password))

    if result.step.name == "ERROR":
        click.echo(f"❌ {result.error}", err=True)
        raise SystemExit(1)

    # Save session
    run_async(client_manager.save_session())
    click.echo("✅ Авторизован успешно")


@auth_group.command("status")
@click.option("--profile", default="default", help="Имя профиля")
def auth_status(profile):
    """Проверить статус авторизации."""
    host = get_host()
    auth_service = host.get(AuthService)
    result = run_async(auth_service.check_session())
    if result.step.name == "SUCCESS":
        click.echo("✅ Авторизован")
    else:
        click.echo(f"❌ Не авторизован. {result.error or 'Выполните: tg-exporter auth login'}")


@auth_group.command("logout")
@click.option("--profile", default="default", help="Имя профиля")
def auth_logout(profile):
    """Выйти из аккаунта."""
    host = get_host()
    auth_service = host.get(AuthService)
    run_async(auth_service.logout())
    click.echo("✅ Выполнен выход из аккаунта")


@auth_group.command("export-session")
@click.option("--output", default=DEFAULT_SECRETS_EXPORTED_ENV_FILENAME, help="Путь к выходному файлу")
def auth_export_session(output):
    """Экспортировать сессию в secrets.exported.env для CI/CD."""
    host = get_host()
    config = host.get(StaticConfig)
    secret_store = host.get(ISecretStore)
    auth_service = host.get(AuthService)

    session_str = secret_store.get(SESSION) or ""
    if not session_str:
        click.echo("❌ Нет активной сессии. Сначала выполните auth login.", err=True)
        raise SystemExit(1)

    api_id = config.api_id
    api_hash = secret_store.get(API_HASH) or ""

    auth_service.export_session(ExportSessionParams(
        api_id=api_id,
        api_hash=api_hash,
        session_string=session_str,
        output_path=Path(output),
    ))

    click.echo(f"✅ Сессия экспортирована в {output}")
    click.echo("⚠️  Файл содержит полный доступ к вашему аккаунту Telegram. Храните его в безопасном месте.")


@auth_group.command("verify")
@click.option("--profile", default="default", help="Имя профиля")
def auth_verify(profile):
    """Проверить валидность сессии (для CI/CD). Exit codes: 0=валидна, 1=невалидна, 2=нет сессии."""
    host = get_host()
    auth_service = host.get(AuthService)
    result = run_async(auth_service.check_session())
    if result.step.name == "SUCCESS":
        click.echo("✅ Сессия валидна")
        raise SystemExit(0)
    else:
        click.echo(f"❌ Сессия невалидна: {result.error or 'нет сессии'}")
        raise SystemExit(1)
