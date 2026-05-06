# План: Консольная утилита Telegram Exporter

## 1. Цели

Создать консольную утилиту `tg-exporter`, которая:

- Выгружает сообщения из Telegram-каналов/чатов в JSON и Markdown
- Поддерживает инкрементальный экспорт (только новые сообщения)
- Полностью настраивается через параметры командной строки и конфиг-файл
- Переиспользует существующую кодовую базу десктопного приложения

**Чего утилита НЕ делает:**
- Не планирует периодический запуск — это задача внешнего планировщика (cron, systemd timer, launchd). CLI — stateless утилита для одного запуска.
- Не имеет GUI — только stdout/stderr и файловый вывод.

## 2. CLI-фреймворк

**Выбор: Click**

| Критерий | Click | Typer | argparse |
|----------|-------|-------|----------|
| Зависимости | ✅ лёгкий | ⚠️ обёртка над click | ✅ stdlib |
| Декларативность | ✅ декораторы | ✅ type hints | ❌ ручной парсинг |
| Вложенные команды | ✅ группы | ✅ группы | ⚠️ subparsers |
| Валидация | ✅ встроенная | ✅ через type hints | ❌ вручную |
| Документированность | ✅ отличная | ⚠️ хуже | ✅ stdlib |

Click — золотая середина. Каждая команда — отдельный `.py` файл (модульная структура, не пихать всё в один файл). Читаемые декораторы, встроенный `--help`.

## 3. DI-контейнер

В приложение внедряется Dependency Injection. Все зависимости собираются в одном месте — контейнере.

```python
# tg_exporter_cli/container.py

class Container:
    """Собирает и предоставляет все зависимости CLI-приложения."""

    def __init__(self, config_path: Path, env_file: Path | None = None):
        # 1. Секреты (порядок: env vars → .env file → keyring)
        self.secret_provider = ChainSecretProvider([
            EnvSecretProvider(env_file),
            KeyringSecretProvider(),
        ])

        # 2. Конфиг (публичные настройки, без секретов)
        self.config = ConfigManager(config_path)

        # 3. Credentials (api_hash, session — через SecretProvider)
        self.credentials = CredentialsManager(self.secret_provider)

        # 4. Telegram-клиент
        self.client_manager = TelegramClientManager(
            self.config, self.credentials
        )

        # 5. Профили
        self.profile_manager = ProfileManager(
            self.credentials, self.config
        )

        # 6. Auth
        self.auth_service = AuthService(self.client_manager)

        # 7. Экспорт
        self.orchestrator = ExportOrchestrator(
            self.client_manager, self.config
        )

    def get_chat_list_service(self):
        """Ленивая инициализация сервиса чатов."""
        return ChatListService(self.client_manager)
```

**Почему свой контейнер, а не dependency-injector:**
- Нулевые зависимости
- Полный контроль над порядком инициализации
- Явные ошибки на старте, а не в рантайме
- Прозрачно для отладки

## 4. Архитектура

```
tg_exporter_cli/          # Новый пакет (модульный: каждая команда — свой файл)
├── __init__.py
├── main.py               # Точка входа (click group)
├── container.py           # DI-контейнер
├── commands/
│   ├── __init__.py
│   ├── auth.py           # Аутентификация
│   ├── export.py         # Экспорт (один чат, --last N)
│   ├── chats.py          # Список чатов, добавление в конфиг
│   ├── profile.py        # Управление аккаунтами
│   └── config_cmd.py     # Управление конфигом
├── config.py             # CLI-конфиг (YAML)
├── secrets/              # Абстракция над источниками секретов
│   ├── __init__.py
│   ├── provider.py       # SecretProvider (ABC)
│   ├── keyring_provider.py    # Системный Keyring
│   ├── env_provider.py        # .env-файлы + переменные окружения
│   └── chain_provider.py      # Цепочка: пробует несколько провайдеров
└── output.py             # Форматированный вывод (таблицы, прогресс)

tg_exporter/              # Существующий код (переиспользуем)
├── core/                 # AuthService, ClientManager, Orchestrator
├── services/             # MediaDownloader, Transcription, Analytics
├── exporters/            # JsonExporter, MarkdownExporter
├── models/               # AppConfig, ExportTask, ExportMessage
└── utils/                # CancellationToken, Logger
```

## 5. Команды

### 5.1. `tg-exporter auth login`

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
1. Читает `api_id`/`api_hash` из опций → env vars → SecretProvider
2. Отправляет код на телефон (интерактивный ввод)
3. Запрашивает код подтверждения
4. При 2FA — запрашивает пароль
5. Сохраняет сессию через `SecretProvider`

### 5.2. `tg-exporter auth status`

```
tg-exporter auth status [OPTIONS]

Options:
  --profile TEXT    Имя профиля

Output:
  ✅ Авторизован как @username (+7999...)
  ❌ Не авторизован. Выполните: tg-exporter auth login
```

### 5.3. `tg-exporter auth logout`

```
tg-exporter auth logout [OPTIONS]
Options:
  --profile TEXT    Имя профиля
```

### 5.4. `tg-exporter export`

Экспорт одного чата/канала.

```
tg-exporter export [OPTIONS]

Chat selection (обязательно одно из):
  --chat TEXT             ID или username чата/канала

Export options:
  --output PATH           Директория для выгрузки (по умолчанию: ./export/{chat_name})
  --format [json|markdown|both]   Формат (по умолчанию: both)

Filter options:
  --date-from DATE        Начало периода (YYYY-MM-DD)
  --date-to DATE          Конец периода (YYYY-MM-DD)
  --days INTEGER          Последние N дней (вместо date-from/date-to)
  --last INTEGER          Экспортировать последние N сообщений (режим тестирования)
  --topic-id INTEGER      ID топика (для форумов)

Media options:
  --download-media        Скачивать медиафайлы
  --transcribe            Транскрибировать голосовые
  --transcriber [local|deepgram]  Провайдер транскрипции

Analytics:
  --analytics             Собирать аналитику (top_authors.md, activity.md)

Markdown options:
  --words-per-file INTEGER   Слов на Markdown-файл (по умолчанию: 50000)

Profile:
  --profile TEXT          Использовать определённый аккаунт
```

**Режим `--last N`:**
- Экспортирует только последние N сообщений чата
- Не сохраняет export_history (тестовый режим)
- Предназначен для отладки и тестирования на больших чатах без полного экспорта

**Режим `--days N`:**
- Экспортирует сообщения за последние N дней
- Удобно для периодического запуска через внешний cron

### 5.5. `tg-exporter chats`

Просмотр и управление списком чатов для экспорта. Удобно добавлять чаты в конфиг через консоль, смотреть по папкам Telegram, выбирать для экспорта.

```
tg-exporter chats list                       # Список всех чатов
tg-exporter chats list --folder "Работа"     # Чаты в конкретной папке
tg-exporter chats list --folders             # Только список папок
tg-exporter chats list --search "кот"        # Поиск по названию
tg-exporter chats show --chat CHAT_ID        # Информация о чате
tg-exporter chats add --chat CHAT_ID         # Добавить чат в конфиг
tg-exporter chats add --folder "Работа"      # Добавить всю папку в конфиг
tg-exporter chats remove --chat CHAT_ID      # Убрать чат из конфига
```

**Вывод `list`:**
```
╔══════════╦══════════════════════════════╦══════════╦════════════╗
║ ID       ║ Название                    ║ Тип      ║ Папка      ║
╠══════════╬══════════════════════════════╬══════════╬════════════╣
║ -1001234 ║ Коты и котики               ║ channel  ║ Развлечения║
║ 12345678 ║ Иван Петров                 ║ user     ║ —          ║
║ -1005678 ║ Рабочая группа              ║ group    ║ Работа     ║
╚══════════╩══════════════════════════════╩══════════╩════════════╝
```

**Идея:** пользователь заходит в консоль, смотрит список чатов с группировкой по папкам, выбирает нужные и добавляет их в конфиг. После этого можно делать `tg-exporter export --chat ID` без необходимости каждый раз искать ID.

### 5.6. `tg-exporter profile`

Управление несколькими аккаунтами (переиспользует `ProfileManager`).

```
tg-exporter profile list
tg-exporter profile add --phone +7999... --api-id 123 --api-hash abc...
tg-exporter profile remove --phone +7999...
tg-exporter profile switch --phone +7999...
```

### 5.7. `tg-exporter config`

Управление конфигурацией.

```
tg-exporter config show                     # Показать текущий конфиг
tg-exporter config set api_id 123           # Установить значение
tg-exporter config set transcriber deepgram
tg-exporter config set secrets_source env   # env | keyring | chain (по умолчанию chain)
tg-exporter config path                     # Показать путь к конфиг-файлу
```

## 6. Аутентификация и секреты

### SecretProvider — абстракция над источниками секретов

Вместо жёсткой привязки к Keyring — абстрактный `SecretProvider`. Поддерживаются три источника:

```python
class SecretProvider(ABC):
    """Источник секретов (api_hash, session, токены)."""

    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> None: ...
    def delete(self, key: str) -> bool: ...
```

| Провайдер | Источник | Когда использовать |
|-----------|----------|--------------------|
| `EnvSecretProvider` | Переменные окружения + `.env` файл | CI/CD, Docker, автоматизация |
| `KeyringSecretProvider` | Системный Keyring | Локальное использование, десктоп |

### ChainSecretProvider

Объединяет несколько провайдеров в цепочку. При чтении — первый не-`None` результат. При записи — пишет во все провайдеры.

```python
# Порядок: сначала проверяем env, потом keyring
provider = ChainSecretProvider([
    EnvSecretProvider(env_file=Path(".env")),
    KeyringSecretProvider(),
])
```

### Формат переменных в .env / env vars

```bash
# .env
TG_EXPORTER_API_ID=123456
TG_EXPORTER_API_HASH=abcdef1234567890abcdef1234567890
TG_EXPORTER_SESSION=1BQANOTEuMTAu...
TG_EXPORTER_DEEPGRAM_KEY=abc123...
```

Приоритет: переменная окружения > `.env` файл > Keyring.

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

### Неинтерактивный режим (CI/CD)

Для CI/CD и неинтерактивных сред — через `.env` файл или переменные окружения:

```bash
export TG_EXPORTER_API_ID=12345678
export TG_EXPORTER_API_HASH=abcdef1234567890abcdef1234567890
export TG_EXPORTER_SESSION=1BQANOTEuMTAu...  # сессия должна быть получена заранее

tg-exporter export --chat -1001234
```

Сессия должна быть уже сохранена (получена через `tg-exporter auth login` в интерактивном режиме на машине где Keyring доступен, затем экспортирована в `.env`).

## 7. ExportHistory — на каждый чат свой файл

История экспорта для инкрементального режима хранится в папке с данными чата, а не в глобальном файле.

```
exports/
└── Коты и котики/
    ├── result.json
    ├── chat_part_1.md
    ├── media/
    └── export_history.json           # история экспорта этого конкретного чата
```

**Формат `export_history.json`:**
```json
{
    "last_message_id": 45678,
    "last_export_date": "2025-06-01T12:00:00+00:00",
    "total_exported": 12340
}
```

**Логика инкрементального экспорта:**
1. Перед экспортом читаем `{output_dir}/export_history.json`
2. Если файл есть → `min_id = last_message_id`, экспортируем только сообщения с ID > `min_id`
3. После экспорта обновляем `export_history.json`
4. Если файла нет → полный экспорт с первого сообщения
5. Флаг `--last N` или `--date-from`/`--date-to` → export_history не обновляется

**Преимущества:**
- Данные чата самодостаточны: можно скопировать папку на другую машину и инкрементальный экспорт продолжит работать
- Не завязываемся на `~/.tg_exporter` который может быть удалён/перемещён
- Логично: история экспорта — часть данных чата

## 8. Вывод и прогресс

### Форматирование

- **Таблицы:** через `rich` (опционально) или простой ASCII (fallback)
- **Прогресс-бар:** через `rich.progress` или `tqdm`
- **Уровни:** `--quiet` (только ошибки), `--verbose` (подробный лог)

### Пример прогресса при экспорте

```
Экспорт "Коты и котики"...
  Сообщений: [████████████████░░░░] 80% (800/1000)
  Медиа:     [████████░░░░░░░░░░░░] 40% (40/100)
  Статус: скачивание медиа...
```

## 9. Конфигурация CLI

Файл `~/.tg_exporter/cli_config.yaml`:

```yaml
# Telegram API
api_id: "12345678"
# api_hash хранится через SecretProvider, не здесь

# Профиль по умолчанию
default_profile: "main"

# Чаты, добавленные через `tg-exporter chats add` (для удобства)
chats:
  - name: "Коты и котики"
    id: -1001234567890
  - name: "Tech News"
    id: -1009876543210

# Настройки по умолчанию для всех экспортов
defaults:
  format: markdown
  words_per_file: 50000
  analytics: false
  download_media: false
  transcribe: false

# Транскрипция
transcription:
  provider: local               # local | deepgram
  local_model: base             # tiny | base | small | medium | large
  language: multi               # multi | ru | en

# Источник секретов
secrets_source: chain            # env | keyring | chain

# Логирование
logging:
  level: INFO
  file: ~/.tg_exporter/cli.log
```

Конфиг содержит только публичные настройки и список чатов для быстрого доступа. Секреты — строго через SecretProvider.

## 10. Стратегия переиспользования

### Что берём из десктопного приложения (без изменений)

| Модуль | Путь | Зачем |
|--------|------|-------|
| `AuthService` | `core/auth/` | Аутентификация в Telegram |
| `TelegramClientManager` | `core/client.py` | Управление клиентом Telethon |
| `CredentialsManager` | `core/credentials.py` | Хранение секретов (адаптировать под SecretProvider) |
| `ProfileManager` | `core/profiles/` | Мульти-аккаунты |
| `ExportOrchestrator` | `core/orchestrator.py` | Главный цикл экспорта |
| `Converter` | `core/converter.py` | Telethon → ExportMessage |
| `JsonExporter` | `exporters/json_exporter.py` | JSON-экспорт |
| `MarkdownExporter` | `exporters/markdown_exporter.py` | Markdown-экспорт |
| `MediaDownloader` | `services/media_downloader/` | Скачивание медиа |
| `TranscriptionService` | `services/transcription/` | Транскрипция аудио |
| `AnalyticsCollector` | `services/analytics/` | Аналитика |
| `ExportHistory` | `services/export_history.py` | Инкрементальный экспорт (доработать: хранение в папке чата) |
| `CancellationToken` | `utils/cancellation.py` | Отмена операций (Ctrl+C) |
| `AppLogger` | `utils/logger.py` | Логирование с редактированием |
| `ExportTask`, `ExportMessage` | `models/` | Модели данных |

### Что НЕ берём

| Модуль | Причина |
|--------|---------|
| `ui/` (весь) | Десктопный UI на customtkinter |
| `BackgroundWorker` | Очередь событий для UI |
| `EventDispatcher` | Роутинг UI-событий |
| `AppConfig` | Модель конфига десктопного приложения (используем `CliConfig`) |

### Что создаём заново

| Модуль | Описание |
|--------|----------|
| `tg_exporter_cli/main.py` | Click-группа, точка входа |
| `tg_exporter_cli/container.py` | DI-контейнер |
| `tg_exporter_cli/config.py` | Модель CLI-конфига (YAML) |
| `tg_exporter_cli/commands/auth.py` | Команды аутентификации |
| `tg_exporter_cli/commands/export.py` | Команда экспорта |
| `tg_exporter_cli/commands/chats.py` | Команда просмотра и управления чатами |
| `tg_exporter_cli/commands/profile.py` | Управление профилями |
| `tg_exporter_cli/commands/config_cmd.py` | Управление конфигом |
| `tg_exporter_cli/secrets/` | SecretProvider, EnvProvider, KeyringProvider, ChainProvider |
| `tg_exporter_cli/output.py` | Форматированный вывод (таблицы, прогресс-бары) |
| `pyproject.toml` (обновить) | Скрипт `tg-exporter` в `[project.scripts]` |

## 11. Фазы реализации

### Фаза 1: Базовая инфраструктура (MVP)

- [ ] Установить `click`, `pyyaml`, `python-dotenv` в зависимости
- [ ] Создать `tg_exporter_cli/secrets/` — SecretProvider, EnvProvider, KeyringProvider, ChainProvider
- [ ] Создать `tg_exporter_cli/container.py` с DI-контейнером
- [ ] Адаптировать `CredentialsManager` под `SecretProvider`
- [ ] Создать `tg_exporter_cli/main.py` с точкой входа
- [ ] Реализовать `auth login` / `auth status` / `auth logout`
- [ ] Реализовать `export` с минимальными опциями (--chat, --output, --format)
- [ ] Проверить сквозной сценарий: логин → экспорт одного чата

### Фаза 2: Полноценный экспорт и чаты

- [ ] Добавить все опции экспорта (фильтры, медиа, транскрипция, аналитика)
- [ ] Реализовать `--last N` для тестирования больших объёмов
- [ ] Реализовать `--days N` для периодического экспорта
- [ ] Доработать `ExportHistory` — хранение в папке чата вместо глобального файла
- [ ] Реализовать `chats list` / `chats show` / `chats add` / `chats remove`
- [ ] Поиск по названию, фильтрация по папкам Telegram
- [ ] Прогресс-бар в консоли

### Фаза 3: Конфигурация и профили

- [ ] Создать модель `CliConfig` (YAML)
- [ ] Реализовать `config show/set`
- [ ] Реализовать `profile list/add/remove/switch`
- [ ] Интеграция `chats add` с конфиг-файлом

### Фаза 4: CI/CD и пакетирование

- [ ] Обновить `pyproject.toml` с entry point `tg-exporter`
- [ ] Добавить `pip install` инструкцию в README
- [ ] Обновить CI для сборки CLI (PyPI package, single binary?)
- [ ] Документировать интеграцию с cron/systemd timer (внешний планировщик)

## 12. Пример использования

### Разовый экспорт

```bash
# Полный экспорт чата в Markdown
tg-exporter export --chat -1001234567890 --format markdown

# Экспорт за последние 7 дней
tg-exporter export --chat "@tech_news" --days 7 --download-media

# Экспорт с транскрипцией и аналитикой
tg-exporter export --chat "@podcast_channel" --transcribe --analytics --format both

# Тестовый экспорт: последние 100 сообщений
tg-exporter export --chat -1001234567890 --last 100

# Экспорт конкретного топика форума
tg-exporter export --chat -1001234567890 --topic-id 42 --format json
```

### Просмотр и выбор чатов

```bash
# Какие чаты доступны?
tg-exporter chats list

# Только папки
tg-exporter chats list --folders

# Чаты в папке "Работа"
tg-exporter chats list --folder "Работа"

# Поиск
tg-exporter chats list --search "кот"

# Добавить в конфиг для быстрого доступа
tg-exporter chats add --chat -1001234567890
tg-exporter chats add --folder "Работа"

# Экспорт чата из конфига (по ID)
tg-exporter export --chat -1001234567890
```

### Интеграция с внешним планировщиком (cron)

CLI не содержит встроенного планировщика. Внешний процесс вызывает утилиту когда нужно.

```bash
# Ежедневный экспорт в 3:00 (crontab)
0 3 * * * cd /home/user/exports && tg-exporter export --chat -1001234 --days 1 --format both --quiet >> /var/log/tg-export.log 2>&1

# Раз в 6 часов через systemd timer
# tg-export.service: Type=oneshot, ExecStart=tg-exporter export --chat -1001234 --days 1
# tg-export.timer: OnCalendar=*:00/6
```

## 13. Риски и ограничения

| Риск | Митигация |
|------|-----------|
| Keyring в headless-окружении | SecretProvider с fallback на .env файл |
| Интерактивный ввод кода при первом логине | CI/CD-friendly: только если сессия уже сохранена через `auth login` |
| Долгий экспорт больших каналов | `--last N` для тестирования, прогресс-бар для информации |
| Разные часовые пояса | Все даты в ISO 8601 с timezone, как в ExportMessage |
| Конфликт с десктопным профилем | Использовать тот же Keyring и тот же `ProfileManager` — единый список аккаунтов |

## 14. Зависимости

Новые (добавить в requirements.txt):
```
click>=8.1,<9.0
pyyaml>=6.0,<7.0
python-dotenv>=1.0,<2.0
rich>=13.0            # таблицы и прогресс-бары в консоли
```

Уже существующие (переиспользуются):
```
telethon, keyring, imageio-ffmpeg,
faster-whisper, PySocks
```

Примечание: `customtkinter` остаётся в requirements.txt для обратной совместимости с десктопным приложением, но CLI-утилита его не импортирует.
