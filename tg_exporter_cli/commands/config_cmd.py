"""Команды управления конфигурацией: show, set, path, init."""
from __future__ import annotations

import json

import click

from tg_exporter.configs.configuration_provider import ConfigurationResult, resolve_config_dir
from tg_exporter.configs.static_config import StaticConfig

from ..hosting import get_host

# Дефолтный config.json — генерируется из StaticConfig, чтобы не дублировать значения
_DEFAULT_CONFIG: dict = StaticConfig().to_dict()


def _merge_defaults(existing: dict, defaults: dict, prefix: str = "") -> list[str]:
    """Рекурсивно добавляет в existing отсутствующие ключи из defaults.
    Возвращает список добавленных путей (например, ['api_id', 'transcription.provider']).
    Существующие значения не перезаписывает.
    """
    added: list[str] = []
    for key, default_value in defaults.items():
        path = f"{prefix}.{key}" if prefix else key
        if key not in existing:
            existing[key] = default_value
            added.append(path)
        elif isinstance(default_value, dict) and isinstance(existing[key], dict):
            added.extend(_merge_defaults(existing[key], default_value, path))
    return added


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
    click.echo(
        f"Retry:       {config.retry_max_attempts} попыток, "
        f"{config.retry_delay_seconds}s–{config.retry_max_delay_seconds}s"
    )
    click.echo(
        f"Rate limit:  media {config.rate_limit_media_download_delay_ms}ms, "
        f"msg {config.rate_limit_message_fetch_delay_ms}ms"
    )


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
    host.get(StaticConfig)

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
    except ValueError as e:
        click.echo(f"❌ Неверное значение для {key}: {value}", err=True)
        raise SystemExit(1) from e

    click.echo(f"✅ {key} = {parsed}")
    click.echo("⚠ Установка через config set временно не сохраняется в файл. Отредактируйте config.json вручную.")


@config_group.command("path")
def config_path():
    """Показать путь к конфиг-файлу."""
    host = get_host()
    result = host.get(ConfigurationResult)
    click.echo(str(result.config_dir / "config.json"))


@config_group.command("init")
@click.option("--force", "-f", is_flag=True, help="Подтвердить обновление существующего конфига.")
def config_init(force: bool):
    """Создать config.json. Если файл уже есть — добавить недостающие поля (требуется --force)."""
    config_dir = resolve_config_dir()
    config_path = config_dir / "config.json"

    if config_path.exists():
        if not force:
            click.echo(
                f"❌ Конфиг уже существует: {config_path}\n"
                f"   Используйте --force чтобы добавить недостающие поля.",
                err=True,
            )
            raise SystemExit(1)

        existing = json.loads(config_path.read_text(encoding="utf-8"))
        added = _merge_defaults(existing, _DEFAULT_CONFIG)
        if not added:
            click.echo(f"✅ Конфиг уже полный, нечего добавлять: {config_path}")
            return
        config_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        click.echo(f"✅ Конфиг обновлён: {config_path}")
        click.echo(f"   Добавлены поля: {', '.join(added)}")
    else:
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(_DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")
        click.echo(f"✅ Конфиг создан: {config_path}")
