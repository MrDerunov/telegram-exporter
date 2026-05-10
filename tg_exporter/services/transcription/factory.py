"""
Фабрика транскриберов — создаёт нужный провайдер по настройкам.
"""

from __future__ import annotations

from .base import BaseTranscriber, TranscriptionError
from ...hosting.static_config import StaticConfig


def create_transcriber(config: StaticConfig) -> BaseTranscriber:
    """
    Создаёт транскрибер по настройкам конфига.

    Args:
        config: StaticConfig с полями transcription_provider, transcription_model, deepgram_api_key

    Returns:
        Нужный BaseTranscriber

    Raises:
        TranscriptionError: Если провайдер не настроен или недоступен
    """
    provider = (config.transcription_provider or "local").strip().lower()

    if provider == "deepgram":
        key = (config.deepgram_api_key or "").strip()
        if not key:
            raise TranscriptionError(
                "Deepgram API ключ не задан. Введите его в настройках."
            )
        from .deepgram_transcriber import DeepgramTranscriber
        return DeepgramTranscriber(api_key=key)

    model_id = (config.transcription_model or "base").strip()

    from .whisper_transcriber import WhisperTranscriber
    return WhisperTranscriber(model_size=model_id)
