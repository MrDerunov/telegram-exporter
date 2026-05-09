"""Команда doctor — диагностика окружения."""
import click
import shutil
from pathlib import Path

from tg_exporter_cli.hosting.cli_config import DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILENAME
from tg_exporter.telegram.auth.auth_service import AuthService
from ..hosting import get_host
from tg_exporter_cli.utils.async_runner import run_async


def _check(ok: bool) -> str:
    return "✅" if ok else "❌"


def _warn(ok: bool) -> str:
    return "✅" if ok else "⚠️"


@click.command("doctor")
def doctor_command():
    """Диагностика окружения."""
    import sys

    # Python
    click.echo(f"{_check(True)} Python {sys.version.split()[0]}")

    # Конфиг
    config_path = DEFAULT_CONFIG_DIR / DEFAULT_CONFIG_FILENAME
    config_ok = config_path.exists()
    click.echo(f"{_check(config_ok)} Конфиг: {config_path} {'(OK)' if config_ok else '(отсутствует)'}")

    # Keyring
    try:
        import keyring
        keyring_ok = True
    except ImportError:
        keyring_ok = False
    click.echo(f"{_warn(keyring_ok)} Keyring: {'доступен' if keyring_ok else 'недоступен (headless)'}")

    # Сессия
    try:
        host = get_host()
        auth_service = host.get(AuthService)
        result = run_async(auth_service.check_session())
        if result.step.name == "SUCCESS":
            click.echo("✅ Сессия: валидна")
        else:
            click.echo(f"⚠️  Сессия: {result.error or 'не найдена'}")
    except Exception as e:
        click.echo(f"⚠️  Сессия: ошибка проверки ({e})")

    # ffmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    click.echo(f"{_warn(ffmpeg_path is not None)} ffmpeg: {ffmpeg_path or 'не найден (нужен для конвертации аудио)'}")

    # Свободное место
    try:
        usage = shutil.disk_usage(Path.home())
        free_gb = usage.free / (1024 ** 3)
        disk_ok = free_gb > 0.1
        click.echo(f"{_warn(disk_ok)} Место на диске: {free_gb:.1f} GB свободно в {Path.home()}")
    except Exception:
        click.echo("⚠️  Место на диске: не удалось проверить")
