# Архитектура Telegram Exporter

## Обзор

**Telegram Exporter** — консольная утилита для экспорта чатов Telegram в JSON и Markdown, с транскрипцией голосовых, скачиванием медиа и поддержкой нескольких аккаунтов.

- **Стек:** Python 3.11+, Click, Telethon, keyring, python-dotenv, faster-whisper
- **Платформы:** macOS, Windows, Linux
- **Лицензия:** MIT

> **Исторически:** проект начинался как десктопное приложение (Tkinter/customtkinter). UI-слой удалён в пользу CLI. Core-слой, сервисы и модели выделены в самостоятельную библиотеку.

## Слои приложения

```
┌──────────────────────────────────────────────────┐
│                 CLI Layer (Click)                 │
│  Container → Commands (export, chats, auth...)   │
├──────────────────────────────────────────────────┤
│                 Core Layer                        │
│  ClientInterface · Auth · Orchestrator           │
├──────────────────────────────────────────────────┤
│              Export Pipeline                      │
│  Orchestrator → Converter → Exporters             │
├──────────────────────────────────────────────────┤
│                Services                           │
│  Media Downloader · Transcription · Analytics    │
│  ExportHistory · SecretProvider                  │
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
tg_exporter_cli/      # CLI-приложение
├── main.py               # Точка входа (click group)
├── container.py           # DI-контейнер
├── config.py             # CLI-конфиг (YAML)
├── output.py             # Форматированный вывод
├── commands/             # Команды (каждая в своём файле)
│   ├── auth.py
│   ├── export.py
│   ├── chats.py
│   ├── profile.py
│   └── config_cmd.py
└── secrets/              # SecretProvider + реализации
    ├── provider.py
    ├── keyring_provider.py
    ├── env_provider.py
    └── chain_provider.py

tg_exporter/          # Core-библиотека
├── core/
│   ├── client_interface.py    # TelegramClientInterface (ABC)
│   ├── telethon_adapter.py    # TelethonClientAdapter (реальная реализация)
│   ├── auth/                  # AuthService + модели
│   │   ├── auth_service.py
│   │   ├── auth_step.py
│   │   └── auth_result.py
│   ├── converter.py           # Telethon → ExportMessage
│   └── orchestrator.py        # ExportOrchestrator
├── exporters/          # Форматы вывода
│   ├── base.py
│   ├── sanitize.py
│   ├── json_exporter.py
│   └── markdown_exporter.py
├── models/             # Типы данных
│   ├── config.py, export_task.py, message.py,
│   ├── export_format.py, export_progress.py,
│   ├── markdown_settings.py, media_type.py,
│   ├── author_filter.py, reaction.py, link.py, poll.py
├── services/           # Бизнес-логика
│   ├── analytics/, media_downloader/, transcription/
│   └── export_history.py
└── utils/              # Инфраструктура
│   ├── cancellation.py
│   └── logger.py

tests/                  # Тесты
├── conftest.py               # Фикстуры (DI-контейнер, фейковый клиент)
├── fakes/
│   ├── fake_telegram_client.py
│   └── factories.py          # Генерация тестовых данных
├── unit/                     # Converter, Exporters, ExportHistory, Secrets, Config
├── integration/              # CLI-команды со всеми параметрами
└── fixtures/                 # Эталонные данные
```

## Ключевые архитектурные решения

### 1. Иммутабельные модели
`ExportMessage`, `ExportTask`, `PollData` — frozen dataclasses. Изменение полей — через `dataclasses.replace()`. Export-пайплайн работает только с этими моделями, не зависит от Telethon.

### 2. Секреты через SecretProvider
`api_hash`, session string, Deepgram API key — хранятся через абстракцию `SecretProvider`. Поддерживаются:
- **Keyring** — системное хранилище (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- **.env файлы** — для CI/CD и автоматизации (`TG_EXPORTER_*`)
- **Переменные окружения** — `TG_EXPORTER_API_HASH`, `TG_EXPORTER_SESSION`

Порядок: переменная окружения > `.env` файл > Keyring. Конфиг-файл содержит только несекретные настройки.

### 3. Абстракция Telegram-клиента
`TelegramClientInterface` (ABC) — контракт для взаимодействия с Telegram API. Две реализации:
- **`TelethonClientAdapter`** — обёртка над реальным `Telethon.TelegramClient`
- **`FakeTelegramClient`** — фейковый клиент для тестов (возвращает предзагруженные сообщения)

Позволяет тестировать всю бизнес-логику без реального Telegram API. Обе реализации проходят один набор тестов на соответствие контракту.

### 4. DI-контейнер
Собирает все зависимости в одном месте. Клиент можно подменить через параметр конструктора (FakeTelegramClient в тестах). Никаких глобальных синглтонов.

### 5. Co-operative cancellation
Длинные операции принимают `CancellationToken`. Проверка на отмену — в каждой итерации. Ctrl+C в CLI → SIGINT → отмена.

### 6. Отсутствие зависимости от Telethon в моделях
Единственная точка контакта с Telethon — `converter.py` (и `telethon_adapter.py`). Все downstream-сервисы работают с чистыми Python-типами через `ExportMessage`.

### 7. Тестируемость на всех уровнях
- **Unit:** Core-логика с `FakeTelegramClient`
- **Integration:** CLI-команды через `Click.testing.CliRunner` + `FakeTelegramClient`
- **Contract:** `TelegramClientInterface` — обе реализации проходят общие тесты
- **Параметризация:** все опции команд тестируются через `@pytest.mark.parametrize`

## Поток данных при экспорте

```
TelegramClientInterface (TelethonAdapter или Fake)
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

## Приложение

- **[CLI Plan](.plans/cli-app.md)** — полный план консольной утилиты, DI-контейнер, команды, тестирование
- **[Core Layer](tg_exporter/core/ARCHITECTURE.md)** — аутентификация, клиент, секреты
- **[Export Pipeline](tg_exporter/core/EXPORT_PIPELINE.md)** — оркестратор, конвертер, экспортёры

## Безопасность

- `api_hash` никогда не пишется в plaintext — только через SecretProvider (Keyring или env)
- Session string хранится через SecretProvider, подгружается только при использовании
- При использовании `.env` — файл должен иметь права `0o600`, добавлен в `.gitignore`
- Логгер автоматически редактирует секреты (api_hash, phone, token) перед записью в лог
- Конфиг-файл имеет права `0o600` на Unix
- Атомарная запись всех файлов (tmp + fsync + os.replace)
