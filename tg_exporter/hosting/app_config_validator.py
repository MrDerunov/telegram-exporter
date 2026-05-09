"""AppConfigValidator — валидация AppConfig."""
from __future__ import annotations

from .app_config import AppConfig

WHISPER_MODELS = ("tiny", "base", "small", "medium", "large", "large-v2", "large-v3")
TRANSCRIPTION_PROVIDERS = ("local", "deepgram")
TRANSCRIPTION_LANGUAGES = ("multi", "ru", "en", "de", "fr", "es", "zh", "ja")


class ConfigValidationError(ValueError):
    pass


def validate_app_config(config: AppConfig) -> None:
    if config.api_id:
        digits = "".join(c for c in config.api_id if c.isdigit())
        if not digits:
            raise ConfigValidationError("api_id must contain digits")

    if config.transcription_provider not in TRANSCRIPTION_PROVIDERS:
        raise ConfigValidationError(
            f"transcription_provider must be one of {TRANSCRIPTION_PROVIDERS}"
        )

    if config.transcription_language not in TRANSCRIPTION_LANGUAGES:
        raise ConfigValidationError(
            f"transcription_language must be one of {TRANSCRIPTION_LANGUAGES}"
        )

    if config.local_whisper_model not in WHISPER_MODELS:
        raise ConfigValidationError(
            f"local_whisper_model must be one of {WHISPER_MODELS}"
        )

    config.markdown.validate()
