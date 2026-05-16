# Transcription Service — транскрипция аудио

Преобразует голосовые сообщения и видеокружки в текст.

## Провайдеры

Оба реализуют `BaseTranscriber` (ABC). Контракт: `preload()` → `transcribe(bytes, mime, lang)` → `unload()`.
Ограничение: 15 минут. Ошибка: `TranscriptionError`.

### WhisperTranscriber (локальный)
faster-whisper на CPU/GPU. Модели: tiny (75 MB) … large-v3 (2.9 GB).
Автоскачивание из HuggingFace, требует 2.5× свободного места.
Колбэки для прогресса скачивания и статуса.

### DeepgramTranscriber (облачный)
Deepgram API. Модели: `nova-3` (EN/multi), `nova-2` (RU/fallback).
Retry: до 3 попыток (exponential backoff 2s→5s). Таймаут: 300s.

## Factory
`create_transcriber(config, deepgram_key) → BaseTranscriber` — выбирает провайдера по `config.transcription_provider` (`"local"` / `"deepgram"`).

## Подготовка аудио (MediaDownloader)
- Voice (голосовое): скачивает OGG → байты
- Video note (кружок): скачивает MP4 → ffmpeg в WAV (16 kHz, mono)
- Ошибки: `MediaTooLongError`, `MediaProcessingError`
