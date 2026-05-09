"""Mapper CliConfig → AppConfig. Переносит все поля включая секреты."""
from __future__ import annotations

from tg_exporter_cli.hosting.cli_config import CliConfig
from tg_exporter.hosting.app_config import AppConfig
from tg_exporter.services.export.markdown_settings import MarkdownSettings


def map_to_app_config(cli_config: CliConfig) -> AppConfig:
    """Маппит CliConfig на AppConfig, перенося все поля включая секреты."""
    return AppConfig(
        api_id=cli_config.api_id,
        api_hash=cli_config.api_hash,
        transcription_provider=cli_config.transcription_provider,
        transcription_language=cli_config.transcription_language,
        local_whisper_model=cli_config.transcription_model,
        deepgram_api_key=cli_config.deepgram_api_key,
        markdown=MarkdownSettings(
            words_per_file=cli_config.default_words_per_file,
        ),
    )
