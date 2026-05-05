# План: Консольная утилита Telegram Exporter

## 1. Цели

Создать консольную утилиту `tg-exporter`, которая:

- Выгружает сообщения из Telegram-каналов/чатов в JSON и Markdown
- Запускается периодически (cron/systemd timer) для автоматической выгрузки
- Поддерживает инкрементальный экспорт (только новые сообщения)
- Полностью настраивается через параметры командной строки и конфиг-файл
- Переиспользует существующую кодовую базу десктопного приложения

## 2. CLI-фреймворк

**Выбор: Click**

| Критерий | Click | Typer | argparse |
|----------|-------|-------|----------|
| Зависимости | ✅ лёгкий | ⚠️ обёртка над click | ✅ stdlib |
| Декларативность | ✅ декораторы | ✅ type hints | ❌ ручной парсинг |
| Вложенные команды | ✅ группы | ✅ группы | ⚠️ subparsers |
| Валидация | ✅ встроенная | ✅ через type hints | ❌ вручную |
| Документированность | ✅ отличная | ⚠️ хуже | ✅ stdlib |

Click — золотая середина. Один `.py` файл на команду, читаемые декораторы, встроенный `--help`.

## 3. Архитектура

```
tg_exporter_cli/          # Новый пакет
├── __init__.py
├── main.py               # Точка входа (click group)
├── commands/
│   ├── __init__.py
│   ├── auth.py           # Аутентификация
│   ├── export.py         # Экспорт
│   ├── profile.py        # Управление аккаунтами
│   └── config_cmd.py     # Управление конфигом
├── config.py             # CLI-конфиг (YAML)
└── scheduler.py          # Режим периодического запуска

tg_exporter/              # Существующий код (переиспользуем)
├── core/                 # AuthService, ClientManager, Orchestrator
├── services/             # MediaDownloader, Transcription, Analytics
├── exporters/            # JsonExporter, MarkdownExporter
├── models/               # AppConfig, ExportTask, ExportMessage
└── utils/                # CancellationToken, Logger
```

## 4. Команды

### 4.1. `tg-exporter auth login`

Интерактивная аутентификация в Telegram.

```
tg-exporter auth login [OPTIONS]

Options:
  --api-id TEXT        Telegram API ID (или из env TG_API_ID)
  --api-hash TEXT      Telegram API Hash (или из env TG_API_HASH)
  --phone TEXT         Номер телефона
  --profile TEXT       Имя профиля (для нескольких аккаунтов)
```

**Процесс:**
1. Читает `api_id`/`api_hash` из опций → env vars → конфиг-файла
2. Отправляет код на телефон (интерактивный ввод)
3. Запрашивает код подтверждения
4. При 2FA — запрашивает пароль
5. Сохраняет сессию в Keyring (через существующий `CredentialsManager`)

### 4.2. `tg-exporter auth status`

```
tg-exporter auth status [OPTIONS]

Options:
  --profile TEXT    Имя профиля

Output:
  ✅ Авторизован как @username (+7999...)
  ❌ Не авторизован. Выполните: tg-exporter auth login
```

### 4.3. `tg-exporter auth logout`

```
tg-exporter auth logout [OPTIONS]
Options:
  --profile TEXT    Имя профиля
```

### 4.4. `tg-exporter export chat`

Экспорт одного чата/канала.

```
tg-exporter export chat [OPTIONS]

Required:
  --chat TEXT             Имя или ID чата/канала

Export options:
  --output PATH           Директория для выгрузки (по умолчанию: ./export)
  --format [json|markdown|both]   Формат (по умолчанию: both)

Filter options:
  --date-from DATE        Начало периода (YYYY-MM-DD)
  --date-to DATE          Конец периода (YYYY-MM-DD)
  --days INTEGER          Последние N дней (вместо date-from/date-to)
  --topic-id INTEGER      ID топика (для форумов)

Media options:
  --download-media        Скачивать медиафайлы
  --transcribe            Транскрибировать голосовые
  --transcriber [local|deepgram]  Провайдер транскрипции

Analytics:
  --analytics             Собирать аналитику (top_authors.md, activity.md)

Incremental:
  --incremental           Только новые сообщения с прошлого экспорта

Markdown options:
  --words-per-file INTEGER   Слов на Markdown-файл (по умолчанию: 50000)

Profile:
  --profile TEXT          Использовать определённый аккаунт
```

### 4.5. `tg-exporter export folder`

Экспорт всех чатов в Telegram-папке.

```
tg-exporter export folder [OPTIONS]

Required:
  --folder TEXT           Название папки Telegram

(остальные опции как у export chat, кроме --chat и --topic-id)
```

### 4.6. `tg-exporter export all`

Экспорт всех доступных чатов.

```
tg-exporter export all [OPTIONS]
(опции как у export chat, кроме --chat и --folder)
```

### 4.7. `tg-exporter profile`

Управление несколькими аккаунтами (переиспользует `ProfileManager`).

```
tg-exporter profile list
tg-exporter profile add --phone +7999... --api-id 123 --api-hash abc...
tg-exporter profile remove --phone +7999...
tg-exporter profile switch --phone +7999...
```

### 4.8. `tg-exporter config`

Управление конфигурацией.

```
tg-exporter config show                     # Показать текущий конфиг
tg-exporter config set --api-id 123         # Установить значение
tg-exporter config set --transcriber deepgram --deepgram-key xxx
tg-exporter config path                     # Показать путь к конфиг-файлу
```

### 4.9. `tg-exporter run`

Основная команда для периодического запуска — экспортирует список каналов согласно конфигу.

```
tg-exporter run [OPTIONS]

Options:
  --config PATH           Путь к конфиг-файлу (по умолчанию: ~/.tg_exporter/cli_config.yaml)
  --channel CHANNEL       Экспортировать конкретный канал (можно повторять)
  --all                   Экспортировать все каналы из конфига (по умолчанию)

Run mode:
  --once                  Один запуск и выход (по умолчанию)
  --watch                 Следить за новыми сообщениями в реальном времени (демон)
  --cron                  Вывести cron-выражение и выйти (для настройки cron)
```

## 5. Конфигурация CLI

Файл `~/.tg_exporter/cli_config.yaml`:

```yaml
# Telegram API
api_id: "12345678"
# api_hash хранится в Keyring, не здесь

# Профиль по умолчанию
default_profile: "main"

# Каналы для автоматического экспорта
channels:
  - name: "My Channel"
    id: -1001234567890          # или username: "channel_username"
    format: markdown
    output: "./export/my_channel"
    incremental: true
    download_media: false
    transcribe: false
    analytics: true
    days: 7                      # или date_from/date_to

  - name: "Tech News"
    id: -1009876543210
    format: both
    output: "./export/tech_news"
    incremental: true
    download_media: true
    transcribe: true
    transcriber: local
    analytics: true

# Настройки по умолчанию для всех каналов
defaults:
  format: markdown
  incremental: true
  words_per_file: 50000
  analytics: false

# Транскрипция
transcription:
  provider: local               # local | deepgram
  local_model: base             # tiny | base | small | medium | large
  language: multi               # multi | ru | en

# Логирование
logging:
  level: INFO
  file: ~/.tg_exporter/cli.log
```

## 6. Аутентификация для CLI

### Поток первого запуска

```
$ tg-exporter auth login
  API ID: 12345678
  API Hash: [скрытый ввод]
  Номер телефона: +79991234567

  📱 Код подтверждения отправлен в Telegram.

  Код: 12345
  ✅ Авторизован как @the_djo (+79991234567)

  Профиль "main" сохранён.
```

### Хранение секретов

Переиспользуется существующий `CredentialsManager`:
- `api_hash` → системный Keyring (`tg_exporter/{api_id}:api_hash`)
- `session string` → Keyring (`tg_exporter/{api_id}:session`)
- `deepgram_key` → Keyring (`tg_exporter/deepgram`)

### Переменные окружения

Для CI/CD и неинтерактивных сред:

```
TG_API_ID=12345678
TG_API_HASH=abcdef1234567890abcdef1234567890
TG_DEEPGRAM_KEY=...
TG_PHONE=+79991234567
TG_PROFILE=main
```

Замечание: сессия должна быть уже сохранена в Keyring (через `tg-exporter auth login`). Без сессии env vars недостаточно — нужно интерактивное подтверждение кода.

## 7. Стратегия переиспользования

### Что берём из десктопного приложения (без изменений)

| Модуль | Путь | Зачем |
|--------|------|-------|
| `AuthService` | `core/auth/` | Аутентификация в Telegram |
| `TelegramClientManager` | `core/client.py` | Управление клиентом Telethon |
| `CredentialsManager` | `core/credentials.py` | Хранение секретов в Keyring |
| `ProfileManager` | `core/profiles/` | Мульти-аккаунты |
| `ExportOrchestrator` | `core/orchestrator.py` | Главный цикл экспорта |
| `Converter` | `core/converter.py` | Telethon → ExportMessage |
| `JsonExporter` | `exporters/json_exporter.py` | JSON-экспорт |
| `MarkdownExporter` | `exporters/markdown_exporter.py` | Markdown-экспорт |
| `MediaDownloader` | `services/media_downloader/` | Скачивание медиа |
| `TranscriptionService` | `services/transcription/` | Транскрипция аудио |
| `AnalyticsCollector` | `services/analytics/` | Аналитика |
| `ExportHistory` | `services/export_history.py` | Инкрементальный экспорт |
| `CancellationToken` | `utils/cancellation.py` | Отмена операций |
| `AppLogger` | `utils/logger.py` | Логирование с редактированием |
| `ExportTask`, `ExportMessage` | `models/` | Модели данных |

### Что НЕ берём

| Модуль | Причина |
|--------|---------|
| `ui/` (весь) | Десктопный UI на customtkinter |
| `BackgroundWorker` | Очередь событий для UI |
| `EventDispatcher` | Роутинг UI-событий |
| `AppConfig` | Модель конфига десктопного приложения (создадим `CliConfig`) |

### Что создаём заново

| Модуль | Описание |
|--------|----------|
| `tg_exporter_cli/main.py` | Click-группа, точка входа |
| `tg_exporter_cli/config.py` | Модель CLI-конфига (YAML) |
| `tg_exporter_cli/commands/auth.py` | Команды аутентификации |
| `tg_exporter_cli/commands/export.py` | Команды экспорта |
| `tg_exporter_cli/commands/profile.py` | Управление профилями |
| `tg_exporter_cli/commands/config_cmd.py` | Управление конфигом |
| `pyproject.toml` (обновить) | Скрипт `tg-exporter` в `[project.scripts]` |

## 8. Фазы реализации

### Фаза 1: Базовая инфраструктура (MVP)

- [ ] Установить `click` в зависимости
- [ ] Создать `tg_exporter_cli/main.py` с точкой входа
- [ ] Реализовать `auth login` / `auth status` / `auth logout`
- [ ] Реализовать `export chat` с минимальными опциями (--chat, --output, --format)
- [ ] Проверить сквозной сценарий: логин → экспорт одного чата

### Фаза 2: Полноценный экспорт

- [ ] Добавить все опции экспорта (фильтры, медиа, транскрипция, аналитика)
- [ ] Реализовать `export folder` и `export all`
- [ ] Интегрировать инкрементальный экспорт через `ExportHistory`
- [ ] Прогресс-бар в консоли (через click.progressbar)

### Фаза 3: Конфигурация и профили

- [ ] Создать модель `CliConfig` (YAML)
- [ ] Реализовать `config show/set`
- [ ] Реализовать `profile list/add/remove/switch`
- [ ] Загрузка каналов из конфиг-файла

### Фаза 4: Периодический запуск

- [ ] Реализовать `tg-exporter run` с поддержкой `--once`
- [ ] Вывод cron-выражения (`--cron`)
- [ ] Проверить интеграцию с cron (пример crontab)
- [ ] Проверить инкрементальный режим при повторных запусках

### Фаза 5: CI/CD и пакетирование

- [ ] Обновить `pyproject.toml` с entry point `tg-exporter`
- [ ] Добавить `pip install` инструкцию в README
- [ ] Обновить CI для сборки CLI (PyPI package, single binary?)

## 9. Пример использования

### Разовый экспорт

```bash
# Экспорт канала за последнюю неделю в Markdown
tg-exporter export chat \
  --chat "@tech_news" \
  --output ./export/tech \
  --format markdown \
  --days 7 \
  --download-media

# Экспорт с транскрипцией и аналитикой
tg-exporter export chat \
  --chat "@podcast_channel" \
  --transcribe \
  --analytics \
  --format both
```

### Настройка периодического экспорта (cron)

```bash
# Показать cron-выражение
tg-exporter run --cron
# → 0 */6 * * * cd /path/to/workdir && tg-exporter run --once

# Добавить в crontab
echo '0 */6 * * * cd /home/user/exports && tg-exporter run --once >> /var/log/tg-exporter.log 2>&1' | crontab -

# Или через конфиг-файл:
tg-exporter run --once --config ~/.tg_exporter/my_channels.yaml
```

## 10. Риски и ограничения

| Риск | Митигация |
|------|-----------|
| Keyring в headless-окружении | Предусмотреть fallback на file-based хранение (с предупреждением о безопасности) |
| Интерактивный ввод кода при первом логине | CI/CD-friendly: только если сессия уже сохранена. Иначе — интерактивный режим. |
| Долгий экспорт больших каналов | Поддержка --limit для тестирования, прогресс-бар для информации |
| Разные часовые пояса | Все даты в ISO 8601 с timezone, как в ExportMessage |
| Конфликт с десктопным профилем | Использовать тот же Keyring и тот же `ProfileManager` — единый список аккаунтов |

## 11. Зависимости

Новые (добавить в requirements.txt):
```
click>=8.1,<9.0
pyyaml>=6.0,<7.0
```

Уже существующие (переиспользуются):
```
telethon, customtkinter (не нужен для CLI), keyring, imageio-ffmpeg,
faster-whisper, PySocks
```

Примечание: `customtkinter` остаётся в requirements.txt для обратной совместимости с десктопным приложением, но CLI-утилита его не импортирует.
