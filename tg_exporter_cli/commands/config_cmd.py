"""Команды управления конфигурацией: show, set, path."""
from __future__ import annotations
import click
import dataclasses

from tg_exporter.hosting.static_config import StaticConfig
from tg_exporter.hosting.configuration_provider import ConfigurationResult
from ..hosting import get_host


@click.group("config")
def config_group():
    """Управление конфигурацией CLI."""
    pass


@config_group.command("show")
def config_show():
    """Показать текущий конфиг."""
    host = get_host()
    config = host.get(StaticConfig)
    result = host.get(ConfigurationResult)

    click.echo(f"Файл:        {result.config_dir / 'config.json'}")
    click.echo(f"API ID:      {config.api_id or '(не задан)'}")
    click.echo(f"Профиль:     {config.default_profile}")
    click.echo(f"Формат:      {config.default_format}")
    click.echo(f"Слов/файл:   {config.default_words_per_file}")
    click.echo(f"Медиа:       {'да' if config.default_download_media else 'нет'}")
    click.echo(f"Транскрипция:{'да' if config.default_transcribe else 'нет'}")
    click.echo(f"Аналитика:   {'да' if config.default_analytics else 'нет'}")
    click.echo(f"Источник секретов: {config.secrets_source}")
    click.echo(f"Логи:        {config.log_level}")
    click.echo(f"Retry:       {config.retry_max_attempts} попыток, {config.retry_delay_seconds}s–{config.retry_max_delay_seconds}s")
    click.echo(f"Rate limit:  media {config.rate_limit_media_download_delay_ms}ms, msg {config.rate_limit_message_fetch_delay_ms}ms")


_SIMPLE_FIELDS = {
    "api_id": str,
    "default_profile": str,
    "default_format": str,
    "default_words_per_file": int,
    "default_download_media": bool,
    "default_transcribe": bool,
    "default_analytics": bool,
    "secrets_source": str,
    "log_level": str,
    "transcription_provider": str,
    "transcription_model": str,
    "transcription_language": str,
    "retry_max_attempts": int,
    "retry_delay_seconds": int,
    "retry_max_delay_seconds": int,
    "rate_limit_media_download_delay_ms": int,
    "rate_limit_message_fetch_delay_ms": int,
}


@config_group.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Установить значение в конфиге. Пример: config set api_id 12345"""
    host = get_host()
    config = host.get(StaticConfig)

    if key not in _SIMPLE_FIELDS:
        valid = ", ".join(sorted(_SIMPLE_FIELDS.keys()))
        click.echo(f"❌ Неизвестный ключ: {key}\nДопустимые: {valid}", err=True)
        raise SystemExit(1)

    target_type = _SIMPLE_FIELDS[key]
    try:
        if target_type is bool:
            parsed = value.lower() in ("true", "1", "yes", "да")
        elif target_type is int:
            parsed = int(value)
        else:
            parsed = value
    except ValueError:
        click.echo(f"❌ Неверное значение для {key}: {value}", err=True)
        raise SystemExit(1)

    click.echo(f"✅ {key} = {parsed}")
    click.echo("⚠ Установка через config set временно не сохраняется в файл. Отредактируйте config.json вручную.")


@config_group.command("path")
def config_path():
    """Показать путь к конфиг-файлу."""
    host = get_host()
    result = host.get(ConfigurationResult)
    click.echo(str(result.config_dir / "config.json"))
