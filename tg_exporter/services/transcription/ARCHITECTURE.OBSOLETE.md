# Transcription Service — транскрипция аудио

## Назначение

Transcription Service преобразует голосовые сообщения и видеокружки в текст. Поддерживает два провайдера: локальный (faster-whisper) и облачный (Deepgram).

## Архитектура

```
create_transcriber(config) → BaseTranscriber
        ├── WhisperTranscriber  (локальный, faster-whisper)
        └── DeepgramTranscriber (облачный, Deepgram API)
```

Оба провайдера реализуют общий интерфейс `BaseTranscriber` (ABC).

## BaseTranscriber (`services/transcription/base.py`)

**Контракт:**
```
preload()                     — предзагрузка модели/соединения
transcribe(bytes, mime, lang) → str | None
unload()                      — освобождение памяти
```

**Ограничение:** `MAX_DURATION_SEC = 15 * 60` (15 минут) — аудио длиннее лимита не транскрибируются.

**Ошибка:** `TranscriptionError` — если провайдер недоступен (нет модели, нет ключа, ошибка API).

## WhisperTranscriber (`services/transcription/whisper_local.py`)

Локальная транскрипция через faster-whisper. Работает офлайн.

**Модели:** tiny (75 MB) → base (140 MB) → small (460 MB) → medium (1.5 GB) → large-v2/v3 (2.9 GB)
**Устройство:** CUDA (float16) или CPU (int8), автоопределение.

**Жизненный цикл загрузки модели:**
1. Проверка наличия в HuggingFace-кеше
2. Проверка свободного места на диске (требуется 2.5× от размера модели)
3. Скачивание через `huggingface_hub.snapshot_download()` с прогресс-баром
4. Инициализация `WhisperModel`
5. После экспорта — `unload()` освобождает память

**Транскрипция:**
- Аудио сохраняется во временный файл (.ogg/.wav)
- `model.transcribe(tmp_path, language=lang, beam_size=1)`
- Сегменты объединяются в строку
- Временный файл удаляется

**Колбэки:** `set_status_callback()` — текст статуса, `set_progress_callback()` — прогресс скачивания модели (0..1).

## DeepgramTranscriber (`services/transcription/deepgram.py`)

Облачная транскрипция через Deepgram API. Не требует локальных моделей.

**Модели:**
- `nova-3` — для английского и multilang (самая свежая/быстрая)
- `nova-2` — для русского и других языков (fallback)

**Параметры запроса:** model, smart_format=true, language.

**Retry-логика:** до 3 попыток с exponential backoff (2s, 5s). Повторяются только 5xx и 429. 4xx — сразу ошибка. Таймаут запроса: 300 секунд.

**Ответ:** извлекает `results.channels[0].alternatives[0].transcript`.

## Factory (`services/transcription/factory.py`)

`create_transcriber(config, deepgram_key) → BaseTranscriber`

Выбирает провайдера по `config.transcription_provider`:
- `"local"` → WhisperTranscriber с моделью из `config.local_whisper_model`
- `"deepgram"` → DeepgramTranscriber с ключом из параметра (не из конфига, ключ хранится в Keyring)

## MediaDownloader (`services/media_downloader/`)

Вспомогательный сервис для скачивания медиа и подготовки аудио к транскрипции.

**Состав пакета:**
- `media_downloader/media_downloader.py` — класс `MediaDownloader` и вспомогательные функции
- `media_downloader/media_dirs.py` — модель `MediaDirs` (пути к поддиректориям)
- `media_downloader/audio_prep_result.py` — модель `AudioPrepResult`
- `media_downloader/errors.py` — `MediaTooLongError`, `MediaProcessingError`

### `download(msg, media_dirs, token) → str | None`
Скачивает медиа из сообщения в нужную поддиректорию:
- `media/photo/` — фото
- `media/video/` — видео, видеокружки, анимации
- `media/audio/` — голосовые, аудио
- `media/documents/` — документы

Стикеры не скачиваются. Каждый вызов проверяет `CancellationToken`.

### `prepare_audio(msg, token) → AudioPrepResult | None`
Готовит аудио к транскрипции:
- **Voice (голосовое):** скачивает OGG, возвращает байты
- **Video note (кружок):** скачивает MP4, конвертирует в WAV через ffmpeg (16 kHz, mono, 16-bit PCM), возвращает байты + сохраняет WAV в `media/audio/`

**Ошибки:**
- `MediaTooLongError` — аудио длиннее 15 минут
- `MediaProcessingError` — не удалось обработать (нет ffmpeg, ошибка конвертации)
