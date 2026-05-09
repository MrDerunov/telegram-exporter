"""CliConfigRepository — загрузка и сохранение CliConfig из/в YAML."""
from __future__ import annotations
from pathlib import Path
import yaml

from .cli_config import CliConfig, ChatEntry
from tg_exporter.utils.file_utils import secure_permissions


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
    # api_hash и deepgram_api_key намеренно исключены — секреты не в YAML
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
    import os
    os.fsync(f.fileno()) if hasattr(f, "fileno") else None
    os.replace(tmp, path)
    secure_permissions(path)
