"""Команда version — информация о версии и окружении."""
import click
import sys
import platform

from tg_exporter.app_constants import VERSION


@click.command("version")
def version_command():
    """Показать версию утилиты."""
    py_ver = sys.version.split()[0]
    os_info = platform.system()
    arch = platform.machine()
    click.echo(f"tg-exporter {VERSION} (python {py_ver}, {os_info} {arch})")
