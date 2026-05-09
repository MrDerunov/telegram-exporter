"""CliConfigRepository — загрузка и сохранение CliConfig из/в YAML."""
from __future__ import annotations
from pathlib import Path
import yaml

from .cli_config import CliConfig


def load_cli_config(path: Path) -> CliConfig:
    if not path.exists():
        return CliConfig()
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    retry = data.get("retry", {})
    rate = data.get("rate_limit", {})
    return CliConfig(
        version=data.get("version", 1),
        api_id=str(data.get("api_id", "")),
        default_profile=data.get("default_profile", "default"),
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
    with open(path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
