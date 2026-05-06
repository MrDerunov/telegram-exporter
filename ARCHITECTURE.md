# Архитектура Telegram Exporter

## Обзор

**Telegram Exporter** — десктопное приложение (Python + Tkinter) для экспорта чатов Telegram в JSON и Markdown, с транскрипцией голосовых, скачиванием медиа и поддержкой нескольких аккаунтов.

- **Стек:** Python 3.11+, Telethon, customtkinter, keyring, faster-whisper
- **Платформы:** macOS (ARM64/Intel), Windows, Linux
- **Лицензия:** MIT

## Слои приложения

```
┌──────────────────────────────────────────────────┐
│                    UI Layer                       │
│  App (контроллер) → Views → Components           │
├──────────────────────────────────────────────────┤
│                 Core Layer                        │
│  Auth · Client · Credentials · Profiles          │
├──────────────────────────────────────────────────┤
│              Export Pipeline                      │
│  Orchestrator → Converter → Exporters             │
├──────────────────────────────────────────────────┤
│                Services                           │
│  Media Downloader · Transcription · Analytics    │
├──────────────────────────────────────────────────┤
│                Data Models                        │
│  AppConfig · ExportTask · ExportMessage          │
└──────────────────────────────────────────────────┘
```

## Правило нейминга

Каждый файл содержит ровно один класс/структуру. Имя файла — snake_case от имени класса:
`AuthService` → `auth_service.py`, `ProfileManager` → `profile_manager.py`.
Никаких обобщённых `models.py` или `service.py`.

## Структура проекта

```
tg_exporter/
├── core/           # Аутентификация, клиент, оркестрация
│   ├── auth/               # Пакет: AuthService + модели
│   │   ├── auth_service.py
│   │   ├── auth_step.py
│   │   └── auth_result.py
│   ├── client.py           # TelegramClientManager
│   ├── credentials.py      # CredentialsManager
│   ├── profiles/           # Пакет: ProfileManager + модель
│   │   ├── profile_manager.py
│   │   └── profile.py
│   ├── converter.py        # Telethon → ExportMessage
│   └── orchestrator.py     # ExportOrchestrator
├── exporters/      # Форматы вывода
│   ├── base.py             # BaseExporter
│   ├── sanitize.py         # sanitize_filename()
│   ├── json_exporter.py    # JsonExporter
│   └── markdown_exporter.py# MarkdownExporter
├── models/         # Типы данных (dataclasses, enums)
│   ├── config.py           # AppConfig
│   ├── markdown_settings.py# MarkdownSettings
│   ├── export_format.py    # ExportFormat, ExportStatus
│   ├── export_task.py      # ExportTask
│   ├── export_progress.py  # ExportProgress
│   ├── author_filter.py    # AuthorFilter
│   ├── message.py          # ExportMessage
│   ├── media_type.py       # MediaType
│   ├── reaction.py         # ReactionItem
│   ├── link.py             # LinkItem
│   ├── poll.py             # PollAnswer, PollData
├── services/       # Бизнес-логика
│   ├── analytics/          # Пакет: аналитика
│   │   ├── analytics_collector.py
│   │   ├── author_stats.py
│   │   ├── analytics_result.py
│   │   └── render.py
│   ├── export_history.py   # ExportHistory
│   ├── media_downloader/   # Пакет: скачивание + конвертация
│   │   ├── media_downloader.py
│   │   ├── media_dirs.py
│   │   ├── audio_prep_result.py
│   │   └── errors.py
│   └── transcription/      # Транскрипция аудио
├── ui/             # Десктопный интерфейс
│   ├── app.py              # App — главный контроллер
│   ├── theme.py            # Дизайн-система
│   ├── components/         # Переиспользуемые виджеты
│   └── views/              # Экраны и модальные окна
├── utils/          # Инфраструктура
│   ├── cancellation.py     # CancellationToken
│   ├── logger.py           # AppLogger
│   └── worker.py           # BackgroundWorker + EventDispatcher
tests/              # Unit-тесты (125 тестов)
scripts/            # Скрипты сборки под все платформы
```

## Ключевые архитектурные решения

### 1. Иммутабельные модели
`ExportMessage`, `ExportTask`, `PollData` — frozen dataclasses. Изменение полей — через `dataclasses.replace()`. Export-пайплайн работает только с этими моделями, не зависит от Telethon.

### 2. Секреты через SecretProvider
`api_hash`, session string, Deepgram API key — хранятся через абстракцию `SecretProvider`. Поддерживаются:
- **Keyring** — системное хранилище (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- **.env файлы** — для CI/CD и автоматизации (`TG_EXPORTER_*`)
- **Переменные окружения** — `TG_EXPORTER_API_HASH`, `TG_EXPORTER_SESSION`

Порядок: переменная окружения > `.env` файл > Keyring. Конфиг-файл `~/.tg_exporter/config.json` содержит только несекретные настройки. Миграция из старого plaintext-формата автоматическая.

### 3. Фоновый поток + Event Queue
Telegram API-вызовы выполняются в одном фоновом потоке (daemon). UI отделён — взаимодействие через thread-safe очередь `UIEvent`. UI опрашивает очередь каждые 80 мс через Tkinter `after()`.

### 4. Co-operative cancellation
Длинные операции (экспорт, скачивание медиа, транскрипция) принимают `CancellationToken`. Проверка на отмену — в каждой итерации и перед каждой IO-операцией. Без принудительного убийства потоков.

### 5. Отсутствие зависимости от Telethon в моделях
Единственная точка контакта с Telethon — `converter.py`. Все downstream-сервисы (экспортёры, аналитика) работают с чистыми Python-типами через `ExportMessage`.

## Поток данных при экспорте

```
Telegram API (Telethon)
        │
        ▼
  converter.py  ──→  ExportMessage (иммутабельный)
        │
        ▼
  ExportOrchestrator  ──┬──→  JsonExporter      → result.json
                        ├──→  MarkdownExporter   → chat_part_1.md, ...
                        ├──→  MediaDownloader    → media/photo|video|audio|docs
                        ├──→  Transcriber        → строка транскрипции
                        ├──→  AnalyticsCollector → top_authors.md, activity.md
                        └──→  ExportHistory      → {chat_export_dir}/export_history.json
```

## Варианты приложения

Проект предоставляет два интерфейса на общем Core-слое:

- **[Desktop UI](tg_exporter/ui/ARCHITECTURE.md)** — графический интерфейс на Tkinter/customtkinter
- **[CLI](CLI_ARCHITECTURE.md)** — консольная утилита на Typer (ручной и автоматизированный экспорт)

## Компонентная документация

Подробное описание ключевых компонентов лежит рядом с кодом, который они описывают:

- [Core Layer](tg_exporter/core/ARCHITECTURE.md) — аутентификация, клиент, секреты, профили
- [Export Pipeline](tg_exporter/core/EXPORT_PIPELINE.md) — оркестратор, конвертер, экспортёры
- [Transcription Service](tg_exporter/services/transcription/ARCHITECTURE.md) — Whisper, Deepgram, конвертация аудио
- [UI Layer](tg_exporter/ui/ARCHITECTURE.md) — контроллер, views, дизайн-система, событийная модель
- [CLI Architecture](CLI_ARCHITECTURE.md) — консольная утилита, DI-контейнер, команды

## Безопасность

- `api_hash` никогда не пишется в plaintext — только через SecretProvider (Keyring или env)
- Session string хранится через SecretProvider, подгружается только при использовании
- При использовании `.env` — файл должен иметь права `0o600`, добавлен в `.gitignore`
- Логгер автоматически редактирует секреты (api_hash, phone, token) перед записью в `app.log`
- Конфиг-файл имеет права `0o600` на Unix
- Атомарная запись всех файлов (tmp + fsync + os.replace)
