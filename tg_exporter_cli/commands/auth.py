"""Команды аутентификации: login, status, logout, export-session, verify."""
import click
from pathlib import Path

from ..hosting import get_host
from ..async_runner import run_async
from tg_exporter.telegram.auth.auth_service import AuthService
from tg_exporter.telegram.telegram_client_manager_interface import ITelegramClientManager
from tg_exporter.secrets import SecretProvider
from tg_exporter.hosting.app_config import AppConfig
from tg_exporter_cli.cli_config import CliConfig


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
    config = host.get(CliConfig)
    app_config = host.get(AppConfig)
    secret_provider = host.get(SecretProvider)
    auth_service = host.get(AuthService)
    client_manager = host.get(ITelegramClientManager)

    # API credentials
    if api_id:
        config.api_id = api_id
        app_config.api_id = api_id
    if api_hash:
        secret_provider.set("TG_EXPORTER_API_HASH", api_hash)
    if not config.api_id:
        config.api_id = click.prompt("API ID")
        app_config.api_id = config.api_id
    if not secret_provider.get("TG_EXPORTER_API_HASH"):
        api_hash = click.prompt("API Hash", hide_input=True)
        secret_provider.set("TG_EXPORTER_API_HASH", api_hash)

    # Phone
    if not phone:
        phone = click.prompt("Номер телефона (+7999...)")

    # Send code
    result = run_async(auth_service.send_code(phone))
    if result.step.name == "ERROR":
        click.echo(f"❌ {result.error}", err=True)
        raise SystemExit(1)

    click.echo("📱 Код отправлен в Telegram")

    # Verify code
    code = click.prompt("Код из Telegram")
    result = run_async(auth_service.verify_code(code))

    if result.step.name == "PASSWORD_REQUIRED":
        password = click.prompt("Пароль 2FA", hide_input=True)
        result = run_async(auth_service.verify_password(password))

    if result.step.name == "ERROR":
        click.echo(f"❌ {result.error}", err=True)
        raise SystemExit(1)

    # Save session
    client_manager.save_session()
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
@click.option("--output", default="secrets.env", help="Путь к выходному файлу")
def auth_export_session(output):
    """Экспортировать сессию в secrets.env для CI/CD."""
    host = get_host()
    client_manager = host.get(ITelegramClientManager)
    config = host.get(CliConfig)
    secret_provider = host.get(SecretProvider)

    # Получаем сессию через адаптер
    client = client_manager.create_client()  # type: ignore[assignment]
    session_str = client.save_session() if hasattr(client, "save_session") else ""

    if not session_str:
        click.echo("❌ Нет активной сессии. Сначала выполните auth login.", err=True)
        raise SystemExit(1)

    api_id = config.api_id
    api_hash = secret_provider.get("TG_EXPORTER_API_HASH") or ""

    output_path = Path(output)
    content = f"TG_EXPORTER_API_ID={api_id}\nTG_EXPORTER_API_HASH={api_hash}\nTG_EXPORTER_SESSION={session_str}\n"
    output_path.write_text(content)
    output_path.chmod(0o600)

    click.echo(f"✅ Сессия экспортирована в {output_path}")
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
