"""Команда version — информация о версии и окружении."""
import click
import sys
import platform


@click.command("version")
def version_command():
    """Показать версию утилиты."""
    py_ver = sys.version.split()[0]
    os_info = platform.system()
    arch = platform.machine()
    click.echo(f"tg-exporter 1.0.0 (python {py_ver}, {os_info} {arch})")
