"""CliConfig — конфигурация CLI-приложения.
Хранится в ~/.tg_exporter/cli_config.yaml.
Не содержит секретов — они через SecretProvider.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml

DEFAULT_CONFIG_DIR = Path.home() / ".tg_exporter"

@dataclass
class CliConfig:
    version: int = 1
    api_id: str = ""
    default_profile: str = "default"
    # Retry settings
    retry_max_attempts: int = 3
    retry_delay_seconds: int = 2
    retry_max_delay_seconds: int = 60
    # Rate limiting
    rate_limit_media_download_delay_ms: int = 500
    rate_limit_message_fetch_delay_ms: int = 100

    @classmethod
    def load(cls, path: Path) -> "CliConfig":
        if not path.exists():
            return cls()
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
        # Секция retry
        retry = data.get("retry", {})
        rate = data.get("rate_limit", {})
        return cls(
            version=data.get("version", 1),
            api_id=str(data.get("api_id", "")),
            default_profile=data.get("default_profile", "default"),
            retry_max_attempts=retry.get("max_attempts", 3),
            retry_delay_seconds=retry.get("delay_seconds", 2),
            retry_max_delay_seconds=retry.get("max_delay_seconds", 60),
            rate_limit_media_download_delay_ms=rate.get("media_download_delay_ms", 500),
            rate_limit_message_fetch_delay_ms=rate.get("message_fetch_delay_ms", 100),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": self.version,
            "api_id": self.api_id,
            "default_profile": self.default_profile,
            "retry": {
                "max_attempts": self.retry_max_attempts,
                "delay_seconds": self.retry_delay_seconds,
                "max_delay_seconds": self.retry_max_delay_seconds,
            },
            "rate_limit": {
                "media_download_delay_ms": self.rate_limit_media_download_delay_ms,
                "message_fetch_delay_ms": self.rate_limit_message_fetch_delay_ms,
            },
        }
        with open(path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
