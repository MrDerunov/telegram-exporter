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
├── cli_config.py          # CLI-конфиг (YAML)
├── output.py              # Форматированный вывод
└── commands/              # Команды (каждая в своём файле)
    ├── auth.py
    ├── export.py
    ├── chats.py
    ├── profile.py
    └── config_cmd.py

tg_exporter/          # Core-библиотека
├── telegram/              # Telegram client, auth, profiles, credentials, converter
│   ├── telegram_client_interface.py  # TelegramClientInterface (ABC)
│   ├── telegram_client_manager.py    # Жизненный цикл клиента
│   ├── telethon_client_adapter.py    # TelethonClientAdapter (реальная реализация)
│   ├── credentials_manager.py        # CredentialsManager
│   ├── converter.py                  # Telethon → ExportMessage
│   ├── auth/                         # AuthService + модели
│   │   ├── auth_service.py
│   │   ├── auth_step.py
│   │   └── auth_result.py
│   └── profiles/                     # ProfileManager
│       ├── profile.py
│       └── profile_manager.py
├── services/
│   ├── export/                       # Export Pipeline + модели + exporters
│   │   ├── export_orchestrator.py    # ExportOrchestrator
│   │   ├── export_message.py         # ExportMessage (иммутабельный)
│   │   ├── export_task.py            # ExportTask
│   │   ├── export_progress.py        # ExportProgress
│   │   ├── export_format.py          # ExportFormat enum
│   │   ├── markdown_settings.py      # MarkdownSettings
│   │   ├── media_type.py             # MediaType enum
│   │   ├── author_filter.py          # AuthorFilter
│   │   ├── reaction_item.py          # ReactionItem
│   │   ├── link_item.py              # LinkItem
│   │   ├── poll_data.py              # PollData
│   │   └── exporters/                # Форматы вывода
│   │       ├── base_exporter.py
│   │       ├── sanitize.py
│   │       ├── json_exporter.py
│   │       └── markdown_exporter.py
│   ├── analytics/                    # Аналитика
│   ├── media_downloader/             # Скачивание медиа
│   ├── transcription/                # Транскрипция
│   └── export_history.py             # История экспорта
├── secrets/                    # SecretProvider + реализации
│   ├── secret_provider.py             # SecretProvider (ABC)
│   ├── keyring_secret_provider.py     # Системный Keyring
│   ├── env_vars_secret_provider.py    # Переменные окружения
│   ├── env_file_secret_provider.py    # .env-файлы
│   └── chain_secret_provider.py       # Цепочка провайдеров
├── hosting/                    # Конфигурация развёртывания
│   └── app_config.py                 # AppConfig
├── ui/                         # ⚠️ Устарело (будет удалено в Фазе 4)
└── utils/                      # Инфраструктура
    ├── cancellation.py
    └── logger.py

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

- **[CLI Plan](.plans/cli-app-plan.md)** — полный план консольной утилиты, DI-контейнер, команды, тестирование
- **[Core Layer](tg_exporter/telegram/ARCHITECTURE.md)** — аутентификация, клиент, секреты
- **[Export Pipeline](tg_exporter/services/export/EXPORT_PIPELINE.md)** — оркестратор, конвертер, экспортёры
- **[Transcription Service](tg_exporter/services/transcription/ARCHITECTURE.md)** — Whisper, Deepgram, конвертация аудио

## Безопасность

- `api_hash` никогда не пишется в plaintext — только через SecretProvider (Keyring или env)
- Session string хранится через SecretProvider, подгружается только при использовании
- При использовании `.env` — файл должен иметь права `0o600`, добавлен в `.gitignore`
- Логгер автоматически редактирует секреты (api_hash, phone, token) перед записью в лог
- Конфиг-файл имеет права `0o600` на Unix
- Атомарная запись всех файлов (tmp + fsync + os.replace)
