# CLI-утилита Telegram Exporter — Архитектура

## Обзор

**Консольная утилита** для экспорта чатов Telegram в JSON и Markdown. Переиспользует
Core-слой и Export Pipeline из десктопного приложения. Предназначена для ручного
и автоматизированного (через внешний планировщик) экспорта.

- **Стек:** Python 3.11+, Telethon, Typer, keyring, python-dotenv
- **Запуск:** `tg-export <команда> [опции]`
- **Аудитория:** консоль, CI/CD, cron-задачи, тестирование больших объёмов

### Что CLI НЕ делает

- **Не планирует переодический экспорт** — для этого есть внешние инструменты (cron, systemd timer, launchd). CLI — stateless утилита для одного запуска.
- **Не имеет GUI** — только stdout/stderr и файловый вывод.
- **Не запускает фоновых процессов** — каждый запуск = одна задача, результат.

---

## Слои CLI-приложения

```
┌──────────────────────────────────────────────────┐
│                 CLI Layer (Typer)                 │
│  commands/export · chats · config · auth         │
├──────────────────────────────────────────────────┤
│                 DI Container                      │
│  container.py — wiring всех зависимостей         │
├──────────────────────────────────────────────────┤
│              Core Layer (общий с GUI)             │
│  Auth · Client · Credentials · Profiles          │
├──────────────────────────────────────────────────┤
│           Secrets Layer (НОВЫЙ)                   │
│  SecretProvider → Keyring | .env | env vars      │
├──────────────────────────────────────────────────┤
│              Export Pipeline (общий с GUI)        │
│  Orchestrator → Converter → Exporters             │
├──────────────────────────────────────────────────┤
│                Services (общие с GUI)             │
│  Media Downloader · Transcription · Analytics    │
│  ExportHistory (на каждый чат)                   │
└──────────────────────────────────────────────────┘
```

---

## Структура CLI-модуля

```
tg_exporter/cli/
├── __init__.py
├── main.py                     # Точка входа: регистрация команд Typer
├── container.py                # DI-контейнер
├── commands/                   # Каждая команда — отдельный модуль
│   ├── __init__.py
│   ├── export.py               # tg-export export [--last N | --chat ID | --all]
│   ├── chats.py                # tg-export chats [list | browse | add]
│   ├── config.py               # tg-export config [show | set]
│   └── auth.py                 # tg-export auth [login | logout | status]
├── secrets/                    # Абстракция над источниками секретов
│   ├── __init__.py
│   ├── provider.py             # SecretProvider (ABC)
│   ├── keyring_provider.py     # Системный Keyring
│   ├── env_provider.py         # .env-файлы и переменные окружения
│   └── chain_provider.py       # Цепочка: пробует несколько провайдеров
└── output.py                   # Форматированный вывод (таблицы, прогресс)
```

---

## DI-контейнер

```python
# container.py

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
        """Сервис получения списка чатов (ленивая инициализация)."""
        return ChatListService(self.client_manager)
```

**Почему свой контейнер, а не dependency-injector:**
- Нулевые зависимости
- Полный контроль над порядком инициализации
- Явные ошибки на старте, а не в рантайме
- Прозрачно для отладки

---

## Команды CLI

### `tg-export export`

Экспорт одного чата.

```
tg-export export --chat CHAT_ID              # Полный экспорт
tg-export export --chat CHAT_ID --last 100   # Последние 100 сообщений (для тестов)
tg-export export --chat CHAT_ID --since 2025-01-01 --to 2025-02-01
tg-export export --chat CHAT_ID --format json
tg-export export --chat CHAT_ID --format markdown
tg-export export --chat CHAT_ID --format both
tg-export export --chat CHAT_ID --no-media
tg-export export --chat CHAT_ID --no-transcribe
tg-export export --chat CHAT_ID --no-analytics
tg-export export --chat CHAT_ID --topic TOPIC_ID
```

**Опции:**
| Опция | Тип | По умолчанию | Описание |
|-------|-----|-------------|----------|
| `--chat` / `-c` | int | *обязательно* | ID чата |
| `--last` / `-n` | int | — | Экспорт последних N сообщений (тестовый режим) |
| `--since` / `-s` | date | — | Сообщения не раньше даты |
| `--to` / `-t` | date | — | Сообщения не позже даты |
| `--format` / `-f` | json\|md\|both | json | Формат вывода |
| `--no-media` | flag | false | Не скачивать медиа |
| `--no-transcribe` | flag | false | Не транскрибировать голосовые |
| `--no-analytics` | flag | false | Не собирать аналитику |
| `--topic` | int | — | ID топика форума |
| `--output` / `-o` | path | ./exports/{chat_name}/ | Директория вывода |

**Режим `--last N`:**
- Экспортирует только последние N сообщений чата
- Не сохраняет export_history (это тестовый режим)
- Предназначен для отладки и тестирования на больших чатах без полного экспорта
- Сообщения идут в порядке от старых к новым (как в обычном экспорте)

**Инкрементальный экспорт:**
- При каждом экспорте рядом с результатами пишется `export_history.json`
- При следующем экспорте этого же чата утилита читает `export_history.json` из папки экспорта
- Экспортируются только сообщения с ID > последнего сохранённого
- Если `export_history.json` отсутствует — полный экспорт с начала

---

### `tg-export chats`

Просмотр и управление списком чатов для экспорта.

```
tg-export chats list                       # Список всех чатов
tg-export chats list --folder "Работа"     # Чаты в конкретной папке
tg-export chats list --folders             # Только список папок
tg-export chats list --search "кот"        # Поиск по названию
tg-export chats add --chat CHAT_ID         # Добавить чат в конфиг для быстрого экспорта
tg-export chats add --folder "Работа"      # Добавить всю папку
tg-export chats remove --chat CHAT_ID      # Убрать чат из конфига
tg-export chats show --chat CHAT_ID        # Информация о чате
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

**Вывод `--folders`:**
```
📁 Развлечения (12 чатов)
📁 Работа (5 чатов)
📁 Новости (8 чатов)
📁 Личное (3 чата)
```

**Идея команды `chats`:** пользователь заходит в консоль, смотрит список чатов с группировкой по папкам, выбирает нужные и добавляет их в конфиг (`chats add`). После этого можно делать `tg-export export --chat ID` без необходимости каждый раз искать ID.

---

### `tg-export auth`

Управление аутентификацией.

```
tg-export auth login                     # Интерактивный вход (phone → code → 2FA)
tg-export auth login --phone +79161234567 --code 12345  # Неинтерактивный
tg-export auth logout                    # Выход
tg-export auth status                    # Проверить статус сессии
tg-export auth profiles                  # Список профилей (аккаунтов)
tg-export auth profiles --switch PHONE   # Переключить активный профиль
```

---

### `tg-export config`

```
tg-export config show                    # Показать текущую конфигурацию
tg-export config set api_id 123456       # Установить api_id
tg-export config set output_dir ./data   # Директория по умолчанию
tg-export config set secrets_source env  # env | keyring | chain (по умолчанию chain)
```

---

## Секреты: Keyring + .env + env vars

### Абстракция SecretProvider

```python
class SecretProvider(ABC):
    """Источник секретов (api_hash, session, токены)."""

    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> None: ...
    def delete(self, key: str) -> bool: ...
```

### Провайдеры

| Провайдер | Источник | Приоритет | Когда использовать |
|-----------|----------|-----------|--------------------|
| `EnvSecretProvider` | Переменные окружения + `.env` файл | Высокий | CI/CD, автоматизация, Docker |
| `KeyringSecretProvider` | Системный Keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service) | Средний | Локальное использование, десктоп |

### ChainSecretProvider

Объединяет несколько провайдеров в цепочку. При чтении — первый не-`None` результат.
При записи — пишет во все провайдеры.

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

---

## ExportHistory — на каждый чат свой файл

**Было (глобальный файл):**
```
~/.tg_exporter/export_history.json    # все чаты в одном файле
```

**Стало (рядом с данными чата):**
```
exports/
└── Коты и котики/
    ├── result.json
    ├── chat_part_1.md
    ├── media/
    └── export_history.json           # история экспорта этого чата
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
5. Флаг `--last N` → export_history не обновляется (тестовый режим)

**Почему рядом с данными, а не глобально:**
- Данные чата самодостаточны: можно скопировать папку на другую машину и инкрементальный экспорт продолжит работать
- Не завязываемся на `~/.tg_exporter` который может быть удалён/перемещён
- Логично: история экспорта — часть данных чата

---

## CLI-вывод и прогресс

### Форматирование

- **Таблицы:** через `rich` (опционально) или простой ASCII (fallback)
- **Прогресс-бар:** через `rich.progress` или простой `tqdm`
- **Цвета:** через `rich` или без цвета в pipe/CI

```python
# Прогресс-бар при экспорте
Экспорт "Коты и котики"...
  Сообщений: [████████████████░░░░] 80% (800/1000)
  Медиа:     [████████░░░░░░░░░░░░] 40% (40/100)
  Статус: скачивание медиа...
```

### Уровни детализации

- `--quiet` / `-q` — только ошибки, подходит для cron
- `--verbose` / `-v` — подробный лог каждого шага
- По умолчанию — прогресс-бар и итоговая статистика

---

## Поток данных CLI-экспорта

```
1. tg-export export --chat -1001234
         │
2. Container собирает зависимости
         │
3. Проверка авторизации (auth status)
         │
4. Чтение export_history.json из output_dir (если есть)
         │
5. ExportOrchestrator.run(task, progress_cb=cli_progress)
         │
6. cli_progress() → обновляет прогресс-бар в консоли
         │
7. Результат:
   - Файлы в output_dir/
   - export_history.json обновлён
   - Статистика в stdout
         │
8. exit(0) — успех / exit(1) — ошибка
```

---

## Интеграция с внешним планировщиком

CLI ничего не знает о планировании. Внешний процесс вызывает утилиту когда нужно.

**Пример crontab (ежедневный экспорт в 3:00 UTC+4):**
```cron
0 3 * * * tg-export export --chat -1001234 --format both --quiet >> /var/log/tg-export.log 2>&1
```

**Пример systemd timer:**
```ini
# tg-export.service
[Unit]
Description=Telegram Export

[Service]
Type=oneshot
ExecStart=/usr/local/bin/tg-export export --chat -1001234 --format both

# tg-export.timer
[Unit]
Description=Daily Telegram Export

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

---

## Файлы конфигурации

```
~/.tg_exporter/
├── config.json              # api_id, настройки вывода, активный профиль
├── profiles.json            # список аккаунтов (телефоны, display_name)
└── app.log                  # лог

exports/                     # директория экспорта по умолчанию
└── {chat_name}/
    ├── result.json
    ├── chat_part_1.md
    ├── media/
    └── export_history.json  # история экспорта этого чата

.env                         # опционально: секреты (api_hash, session)
```

---

## Отличия от десктопной версии

| Аспект | Десктоп (GUI) | CLI |
|--------|---------------|-----|
| Фреймворк | Tkinter / customtkinter | Typer |
| Потоки | Фоновый daemon + Event Queue | Основной поток (блокирующий) |
| Отмена | CancellationToken + кнопка | Ctrl+C (SIGINT) |
| Прогресс | Progress Widget | Progress bar в stdout |
| Секреты | Только Keyring | Keyring + .env + env vars |
| Export History | Глобальный файл | Рядом с данными чата |
| Вывод | Окна и модалы | Таблицы и прогресс-бары |
| Планировщик | Нет (ручной запуск) | Внешний (cron/systemd timer) |

---

## План реализации (поэтапно)

### Этап 1: DI-контейнер и секреты
- `container.py` — сборка зависимостей
- `secrets/` — SecretProvider, KeyringProvider, EnvProvider, ChainProvider
- Миграция `CredentialsManager` на `SecretProvider`

### Этап 2: CLI-каркас и auth
- `main.py` — точка входа Typer
- `commands/auth.py` — login, logout, status

### Этап 3: Команда chats
- `commands/chats.py` — list, browse по папкам, add/remove в конфиг
- Сервис `ChatListService` в core

### Этап 4: Команда export
- `commands/export.py` — полный и инкрементальный экспорт
- Режим `--last N` для тестирования
- Перенос `ExportHistory` в папку чата

### Этап 5: config и полировка
- `commands/config.py`
- `output.py` — таблицы, прогресс-бары
- Интеграционное тестирование
