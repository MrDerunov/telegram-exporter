# Архитектура Telegram Exporter

## Обзор

Консольная утилита для экспорта чатов Telegram в JSON и Markdown.
Стек: Python 3.11+, Click, Telethon, keyring, faster-whisper.

Проект разделён на две части:
- **`tg_exporter/`** — core-библиотека (сервисы, модели, Telegram-клиент). Не зависит от CLI.
- **`tg_exporter_cli/`** — консольный интерфейс (Click-команды, DI-хост).

Правило: один файл = один класс. Имя файла — snake_case от имени класса.

## Слои

```
CLI (Click commands)  →  CliHost (DI)  →  Services  →  Models (frozen dataclasses)
```

- **CLI** — Click-команды, каждая в отдельном файле. Получают сервисы через `get_host().get(Type)`.
- **Hosting/DI** — `CliHost.build()` читает конфиг, маппит в `StaticConfig`/`StateModel`, регистрирует сервисы.
- **Services** — бизнес-логика: экспорт, транскрипция, аналитика, медиа, auth, профили.
- **Models** — иммутабельные frozen dataclasses: `ExportMessage`, `ExportTask`, `StaticConfig`, `StateModel`.

## Ключевые принципы

### Иммутабельные модели
`ExportMessage`, `ExportTask`, `StaticConfig`, `StateModel` — frozen dataclasses.
Изменение только через `dataclasses.replace()`. Модели не зависят от Telethon.

### Абстракция Telegram-клиента
- `TelegramClientInterface` (ABC) — контракт взаимодействия с Telegram API.
- Реализации: `TelethonClientAdapter` (реальная) и `FakeTelegramClient` (для тестов).
- `ITelegramClientManager` (ABC) — жизненный цикл клиента.

### Секреты: ISecretStore
`api_hash`, session, ключи API — через абстракцию `ISecretStore`.
Реализации: `KeyringSecretStore` (системный keyring) или `JsonSecretStore` (secrets.json для CI).
Дополнительно: переменные окружения `TG_EXPORTER_*` и `.env` подхватываются `ConfigurationProvider`.

### Состояние: ISettingsStore
Профили, чаты, активный телефон — через `ISettingsStore` → `StateModel` → `state.json`.

### DI: CliHost
- `build()` — читает конфиг, регистрирует сервисы.
- `run()` — инициализирует логгер.
- `rebind_services()` — переопределение для тестов (подмена клиента на Fake).
- Никаких глобальных синглтонов.

### Отсутствие Telethon в моделях
Единственная точка контакта с Telethon — `converter.py` и `telethon_client_adapter.py`.
Все downstream-сервисы работают с `ExportMessage` (чистые Python-типы).

### Co-operative cancellation
Длинные операции принимают `CancellationToken`. Ctrl+C → отмена.

## Поток данных при экспорте

```
TelegramClientInterface  →  converter  →  ExportMessage
                                              │
                                       ExportOrchestrator
                                         ├── JsonExporter      → result.json
                                         ├── MarkdownExporter   → _part_N.md
                                         ├── MediaDownloader    → media/
                                         ├── Transcriber        → текст
                                         ├── AnalyticsCollector → отчёты
                                         └── ExportHistory      → export_history.json
```

## Хранение конфигов

Директория: `$TELEGRAM_EXPORTER_CONFIG_DIR` или `./`.

```
<config_dir>/
├── config.json    # настройки (без секретов)
├── state.json     # состояние, профили, список чатов
├── secrets.json   # секреты (если secrets_source=file)
├── .env           # переменные окружения (опционально)
└── app.log        # лог
```

Приоритет секретов: env vars (`TG_EXPORTER_*`) > `.env` > `secrets.json` > keyring.
Логгер автоматически редактирует секреты перед записью.

## Детальные описания

- **[Core Layer](tg_exporter/telegram/ARCHITECTURE.md)** — аутентификация, клиент, профили
- **[Export Pipeline](tg_exporter/services/export/EXPORT_PIPELINE.md)** — оркестратор, конвертер, экспортёры
- **[Transcription](tg_exporter/services/transcription/ARCHITECTURE.md)** — Whisper, Deepgram
