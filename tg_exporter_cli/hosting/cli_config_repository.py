"""CliConfigRepository — загрузка и сохранение CliConfig из/в YAML."""
from __future__ import annotations
from pathlib import Path
import yaml

from .cli_config import CliConfig, ChatEntry
from tg_exporter.utils.file_utils import secure_permissions


def load_cli_config(path: Path) -> CliConfig:
    if not path.exists():
        return CliConfig()
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    retry = data.get("retry", {})
    rate = data.get("rate_limit", {})
    transcription = data.get("transcription", {})
    logging_data = data.get("logging", {})
    defaults = data.get("defaults", {})

    # Чаты
    chats_raw = data.get("chats", []) or []
    chats = [ChatEntry(name=c["name"], id=c["id"]) for c in chats_raw if isinstance(c, dict)]

    return CliConfig(
        version=data.get("version", 1),
        api_id=str(data.get("api_id", "")),
        default_profile=data.get("default_profile", "default"),
        chats=chats,
        default_format=defaults.get("format", "both"),
        default_words_per_file=defaults.get("words_per_file", 50000),
        default_download_media=defaults.get("download_media", False),
        default_transcribe=defaults.get("transcribe", False),
        default_analytics=defaults.get("analytics", False),
        transcription_provider=transcription.get("provider", "local"),
        transcription_model=transcription.get("model", "base"),
        transcription_language=transcription.get("language", "multi"),
        secrets_source=data.get("secrets_source", "chain"),
        log_level=logging_data.get("level", "INFO"),
        log_file=logging_data.get("file", ""),
        retry_max_attempts=retry.get("max_attempts", 3),
        retry_delay_seconds=retry.get("delay_seconds", 2),
        retry_max_delay_seconds=retry.get("max_delay_seconds", 60),
        rate_limit_media_download_delay_ms=rate.get("media_download_delay_ms", 500),
        rate_limit_message_fetch_delay_ms=rate.get("message_fetch_delay_ms", 100),
    )


def save_cli_config(config: CliConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": config.version,
        "api_id": config.api_id,
        "default_profile": config.default_profile,
        "chats": [{"name": c.name, "id": c.id} for c in config.chats],
        "defaults": {
            "format": config.default_format,
            "words_per_file": config.default_words_per_file,
            "download_media": config.default_download_media,
            "transcribe": config.default_transcribe,
            "analytics": config.default_analytics,
        },
        "transcription": {
            "provider": config.transcription_provider,
            "model": config.transcription_model,
            "language": config.transcription_language,
        },
        "secrets_source": config.secrets_source,
        "logging": {
            "level": config.log_level,
            "file": config.log_file,
        },
        "retry": {
            "max_attempts": config.retry_max_attempts,
            "delay_seconds": config.retry_delay_seconds,
            "max_delay_seconds": config.retry_max_delay_seconds,
        },
        "rate_limit": {
            "media_download_delay_ms": config.rate_limit_media_download_delay_ms,
            "message_fetch_delay_ms": config.rate_limit_message_fetch_delay_ms,
        },
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
    import os
    os.fsync(f.fileno()) if hasattr(f, "fileno") else None
    os.replace(tmp, path)
    secure_permissions(path)
