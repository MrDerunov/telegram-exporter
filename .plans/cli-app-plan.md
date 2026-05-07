# План: Консольная утилита Telegram Exporter

## 1. Цели

Создать консольную утилиту `tg-exporter`, которая:

- Выгружает сообщения из Telegram-каналов/чатов в JSON и Markdown
- Поддерживает инкрементальный экспорт (только новые сообщения)
- Полностью настраивается через параметры командной строки и конфиг-файл
- Покрыта тестами: основная логика, команды CLI и параметры команд
- Использует фейковый Telegram-клиент для тестирования без реального API

**Чего утилита НЕ делает:**
- Не планирует периодический запуск — это задача внешнего планировщика (cron, systemd timer, launchd)
- Не имеет GUI — только stdout/stderr и файловый вывод

**Десктопное приложение:**
- Десктопное приложение (Tkinter/customtkinter) больше не актуально
- UI-слой (`tg_exporter/ui/`) и его зависимости подлежат удалению
- Core-слой, сервисы, модели и экспортеры выделяются в самостоятельную библиотеку

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

## 3. Telegram-клиент: абстракция и реализации

Для тестирования без реального Telegram API вводится абстракция над клиентом.

```python
# tg_exporter/core/client_interface.py

class TelegramClientInterface(ABC):
    """Контракт для взаимодействия с Telegram API."""

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def is_authorized(self) -> bool: ...
    async def send_code_request(self, phone: str) -> Any: ...
    async def sign_in(self, phone: str, code: str) -> Any: ...
    async def sign_in_password(self, password: str) -> Any: ...
    async def get_dialogs(self, limit: int | None = None) -> list[Dialog]: ...
    async def iter_messages(
        self, peer_id: int, min_id: int = 0,
        offset_date: datetime | None = None,
        limit: int | None = None, ...
    ) -> AsyncIterator[Message]: ...
    async def download_media(self, message: Message, path: Path) -> Path | None: ...
    def save_session(self) -> str: ...
    def load_session(self, session_str: str) -> None: ...
```

### Реализации

| Класс | Назначение |
|-------|------------|
| `TelethonClientAdapter` | Обёртка над реальным `Telethon.TelegramClient` — production |
| `FakeTelegramClient` | Фейковый клиент для тестов — возвращает предзагруженные сообщения |

### FakeTelegramClient

```python
# tests/fakes/fake_telegram_client.py

class FakeTelegramClient(TelegramClientInterface):
    """Фейковый клиент для unit-тестов."""

    def __init__(self):
        self._dialogs: list[Dialog] = []
        self._messages: dict[int, list[Message]] = {}  # peer_id → messages
        self._authorized = False

    def add_dialog(self, dialog: Dialog) -> None: ...
    def add_messages(self, peer_id: int, messages: list[Message]) -> None: ...
    def set_authorized(self, authorized: bool) -> None: ...
```

Фейковый клиент позволяет:
- Предзагружать диалоги и сообщения
- Симулировать авторизацию/неавторизацию
- Проверять что методы были вызваны с правильными параметрами
- Тестировать экспорт на разных объёмах данных без реального API

### DI-контейнер с подменой клиента

```python
# tg_exporter_cli/container.py

class Container:
    """DI-контейнер. В тестах client можно передать извне."""

    def __init__(
        self,
        config_path: Path,
        env_file: Path | None = None,
        telegram_client: TelegramClientInterface | None = None,  # для тестов
    ):
        self.secret_provider = ChainSecretProvider([...])
        self.config = ConfigManager(config_path)
        self.credentials = CredentialsManager(self.secret_provider)

        # Клиент можно подменить (FakeTelegramClient в тестах)
        self.client = telegram_client or TelethonClientAdapter(
            self.config, self.credentials
        )

        self.auth_service = AuthService(self.client)
        self.orchestrator = ExportOrchestrator(self.client, self.config)
        ...
```

## 4. DI-контейнер

```python
# tg_exporter_cli/container.py

class Container:
    """Собирает и предоставляет все зависимости CLI-приложения."""

    def __init__(
        self,
        config_path: Path,
        env_file: Path | None = None,
        telegram_client: TelegramClientInterface | None = None,
    ):
        # 1. Секреты (порядок: env vars → .env file)
        self.secret_provider = ChainSecretProvider([
            EnvVarsSecretProvider(),
            EnvFileSecretProvider(env_file),
        ])  # keyring_provider не подключаем по умолчанию — на headless-системах недоступен

        # 2. Конфиг (публичные настройки, без секретов)
        self.config = ConfigManager(config_path)

        # 3. Credentials (api_hash, session — через SecretProvider)
        self.credentials = CredentialsManager(self.secret_provider)

        # 4. Telegram-клиент (реальный или фейковый для тестов)
        self.client = telegram_client or TelethonClientAdapter(
            self.config, self.credentials
        )

        # 5. Профили
        self.profile_manager = ProfileManager(
            self.credentials, self.config
        )

        # 6. Auth
        self.auth_service = AuthService(self.client)

        # 7. Экспорт
        self.orchestrator = ExportOrchestrator(
            self.client, self.config
        )

    def get_chat_list_service(self):
        """Ленивая инициализация сервиса чатов."""
        return ChatListService(self.client)
```

**Почему свой контейнер, а не dependency-injector:**
- Нулевые зависимости
- Полный контроль над порядком инициализации
- Явные ошибки на старте, а не в рантайме
- Прозрачно для отладки
- Легко подменять реализации для тестов (через параметры конструктора)

## 5. Архитектура

```
tg_exporter_cli/          # CLI-приложение
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
│   ├── env_vars_provider.py   # Переменные окружения (os.environ)
│   ├── env_file_provider.py   # .env-файлы
│   └── chain_provider.py      # Цепочка: пробует несколько провайдеров
└── output.py             # Форматированный вывод (таблицы, прогресс)

tg_exporter/              # Core-библиотека (общая для CLI и тестов)
├── core/
│   ├── client_interface.py    # TelegramClientInterface (ABC) ← НОВОЕ
│   ├── telethon_adapter.py    # TelethonClientAdapter          ← НОВОЕ
│   ├── auth/                  # AuthService + модели
│   ├── converter.py           # Telethon → ExportMessage
│   └── orchestrator.py        # ExportOrchestrator
├── exporters/            # JsonExporter, MarkdownExporter
├── services/             # MediaDownloader, Transcription, Analytics, ExportHistory
├── models/               # ExportTask, ExportMessage, ...
└── utils/                # CancellationToken, Logger

tests/                    # Тесты
├── conftest.py                 # Фикстуры (контейнер, фейковый клиент)
├── fakes/
│   ├── __init__.py
│   ├── fake_telegram_client.py # FakeTelegramClient
│   └── factories.py            # Фабрики тестовых данных (сообщения, диалоги)
├── unit/
│   ├── test_converter.py       # Конвертация Telethon → ExportMessage
│   ├── test_orchestrator.py    # Логика экспорта с фейковым клиентом
│   ├── test_export_history.py  # Инкрементальный экспорт
│   ├── test_exporters.py       # JSON и Markdown экспортеры
│   ├── test_secrets.py         # SecretProvider и все реализации
│   └── test_config.py          # CliConfig, валидация
│   ├── test_cancellation.py    # Отмена во время экспорта, медиа, транскрипции
├── integration/
│   ├── test_export_command.py  # Команда export со всеми параметрами
│   ├── test_chats_command.py   # Команда chats
│   ├── test_auth_command.py    # Команда auth
│   ├── test_config_command.py  # Команда config
│   └── test_profile_command.py # Команда profile
└── fixtures/
    └── sample_messages.json    # Эталонные сообщения для тестов

# Удаляется (десктопное приложение больше не нужно):
# tg_exporter/ui/          ❌ УДАЛИТЬ
# tg_exporter/utils/worker.py  ❌ УДАЛИТЬ (BackgroundWorker, EventDispatcher)
# main.py                  ❌ УДАЛИТЬ (старая точка входа в GUI)
```

## 6. Команды

### 6.1. `tg-exporter auth login`

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

### 6.2. `tg-exporter auth status`

```
tg-exporter auth status [OPTIONS]

Options:
  --profile TEXT    Имя профиля

Output:
  ✅ Авторизован как @username (+7999...)
  ❌ Не авторизован. Выполните: tg-exporter auth login
```

### 6.3. `tg-exporter auth logout`

```
tg-exporter auth logout [OPTIONS]
Options:
  --profile TEXT    Имя профиля
```

### 6.4. `tg-exporter auth export-session`

Экспорт сессии в файл `secrets.env` для CI/CD и headless-систем.

```
tg-exporter auth export-session [OPTIONS]

Options:
  --output PATH     Путь к файлу (по умолчанию: ./secrets.env)
  --profile TEXT    Имя профиля

Output (secrets.env):
  TG_EXPORTER_API_ID=12345678
  TG_EXPORTER_API_HASH=abcdef1234567890abcdef1234567890
  TG_EXPORTER_SESSION=1BQANOTEuMTAu...
```

**Процесс:**
1. Читает текущую сессию и api_hash через SecretProvider
2. Формирует `secrets.env` с нужными переменными
3. Выставляет права `0o600` на файл
4. Выводит предупреждение: «⚠️ Файл содержит полный доступ к вашему аккаунту Telegram. Храните его в безопасном месте.»

### 6.5. `tg-exporter auth verify`

Проверка валидности сессии без интеракции (для CI/CD).

```
tg-exporter auth verify [OPTIONS]

Options:
  --profile TEXT    Имя профиля

Exit codes:
  0 — сессия валидна
  1 — сессия невалидна / протухла
  2 — нет сессии

Output:
  ✅ Сессия валидна (аккаунт @username)
  ❌ Сессия протухла. Выполните: tg-exporter auth login
  ❌ Сессия не найдена.
```

### 6.6. `tg-exporter export`

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
  --resume              Продолжить прерванный экспорт (читает export_history.json)
  --message-types [text|media|pinned|all]  Фильтр по типам сообщений (по умолчанию: all)

Profile:
  --profile TEXT          Использовать определённый аккаунт
```

**Режим `--resume`:**
- Читает `export_history.json` и продолжает с последнего сохранённого сообщения
- Полезно после прерывания Ctrl+C или сетевого сбоя
- Не перезаписывает уже экспортированные файлы

**Режим `--last N`:**
- Экспортирует только последние N сообщений чата
- Не сохраняет export_history (тестовый режим)
- Предназначен для отладки и тестирования на больших чатах без полного экспорта

**Режим `--days N`:**
- Экспортирует сообщения за последние N дней
- Удобно для периодического запуска через внешний cron

### 6.7. `tg-exporter chats`

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

### 6.8. `tg-exporter profile`

Управление несколькими аккаунтами (переиспользует `ProfileManager`).

```
tg-exporter profile list
tg-exporter profile add --phone +7999... --api-id 123 --api-hash abc...
tg-exporter profile remove --phone +7999...
tg-exporter profile switch --phone +7999...
```

### 6.9. `tg-exporter config`

Управление конфигурацией.

```
tg-exporter config show                     # Показать текущий конфиг
tg-exporter config set api_id 123           # Установить значение
tg-exporter config set transcriber deepgram
tg-exporter config set secrets_source env   # env | keyring | chain (по умолчанию chain)
tg-exporter config path                     # Показать путь к конфиг-файлу
```

### 6.10. `tg-exporter export --all`

Массовый экспорт всех чатов из конфига одной командой.

```
tg-exporter export --all [OPTIONS]

Options:
  --format [json|markdown|both]   Формат (по умолчанию: both)
  --download-media                Скачивать медиафайлы
  --transcribe                    Транскрибировать голосовые
  --skip-unavailable              Пропускать недоступные чаты (удалённые, заблокированные)
  --profile TEXT                  Аккаунт
```

### 6.11. `tg-exporter version`

```
tg-exporter version
# tg-exporter 1.0.0 (python 3.12, Linux x86_64)
```

### 6.12. `tg-exporter doctor`

Диагностика окружения.

```
tg-exporter doctor

Output:
  ✅ Python 3.12.3
  ✅ Конфиг: /home/user/.tg_exporter/cli_config.yaml (OK)
  ⚠️ Keyring: недоступен (headless система)
  ✅ Сессия: валидна (аккаунт @username)
  ✅ ffmpeg: 7.0.2 (необходим для конвертации аудио)
  ⚠️ Место на диске: 2.1 GB свободно в export-директории
```

Проверяет: Python, конфиг, keyring, сессию, ffmpeg, свободное место.

## 7. Тестирование

### Стратегия

| Уровень | Что тестируется | Инструменты |
|---------|-----------------|-------------|
| Unit | Core-логика (Converter, ExportHistory, Exporters, SecretProvider, CliConfig) | pytest, FakeTelegramClient |
| Integration | CLI-команды со всеми параметрами, сквозной сценарий экспорта | pytest, Click.testing.CliRunner, FakeTelegramClient |

### Принципы

- **Без реального Telegram API** — все тесты используют `FakeTelegramClient`
- **Параметризация** — одна команда тестируется со всеми комбинациями флагов через `@pytest.mark.parametrize`
- **Snapshots** — эталонный вывод команд (JSON, таблицы) хранится в `tests/fixtures/`
- **Фабрики** — генерация тестовых сообщений/диалогов через `tests/fakes/factories.py`

### Что покрывается тестами обязательно

**Core-логика:**
- `Converter.message_to_export()` — все типы сообщений, все поля
- `ExportHistory` — сохранение/загрузка из папки чата, инкрементальный min_id
- `JsonExporter` / `MarkdownExporter` — формат вывода, разбивка по файлам
- `CancellationToken` — cooperative cancellation: проверка на каждой итерации, частичный результат валиден
- `SecretProvider` — все три провайдера, цепочка, приоритет
- `ExportOrchestrator` — полный цикл с фейковыми сообщениями

**CLI-команды:**
- `export` — все опции: `--format`, `--date-from`, `--date-to`, `--days`, `--last`, `--topic-id`, `--download-media`, `--transcribe`, `--analytics`, `--words-per-file`
- `chats` — `list`, `list --folder`, `list --folders`, `list --search`, `show`, `add`, `remove`, `add --folder`
- `auth` — `login` (все шаги), `status`, `logout`
- `config` — `show`, `set`, `path`
- `profile` — `list`, `add`, `remove`, `switch`

**Интеграционные сценарии:**
- Сквозной: логин → просмотр чатов → экспорт → проверка файлов
- Инкрементальный: экспорт → новые сообщения → повторный экспорт → только новые
- Отмена: Ctrl+C во время экспорта → частичный результат валиден
- Ошибки: неверный chat ID, отсутствие авторизации, битый конфиг

### Пример теста (интеграционный)

```python
# tests/integration/test_export_command.py

def test_export_last_n_messages(cli_runner, container_with_fake_client):
    """Экспорт последних 50 сообщений с фейковым клиентом."""
    fake_client = container_with_fake_client.client
    fake_client.add_messages(-1001234, generate_messages(200))

    result = cli_runner.invoke(
        cli_main,
        ["export", "--chat", "-1001234", "--last", "50", "--format", "json"]
    )

    assert result.exit_code == 0
    assert "Экспорт завершён" in result.output
    assert Path("exports/TestChat/result.json").exists()

    data = json.loads(Path("exports/TestChat/result.json").read_text())
    assert len(data["messages"]) == 50


@pytest.mark.parametrize("format_flag", ["json", "markdown", "both"])
def test_export_formats(cli_runner, container_with_fake_client, format_flag):
    """Экспорт во всех поддерживаемых форматах."""
    ...


@pytest.mark.parametrize("days,expected_count", [
    (1, 5),
    (7, 30),
    (30, 100),
])
def test_export_date_filter(cli_runner, container, days, expected_count):
    """Фильтр по дате выдаёт правильное число сообщений."""
    ...
```

## 8. Аутентификация и секреты

### SecretProvider — абстракция над источниками секретов

```python
class SecretProvider(ABC):
    """Абстракция над источником секретов (api_hash, session, токены)."""
    writable: bool = False  # Может ли провайдер сохранять секреты

    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> None: ...
    def delete(self, key: str) -> None: ...
```

| Провайдер | Источник | writable | Когда использовать |
|-----------|----------|----------|--------------------|
| `EnvVarsSecretProvider` | Переменные окружения (`os.environ`) | ✅ | CI/CD, Docker — секреты инжектятся через env |
| `EnvFileSecretProvider` | `.env` файл | ❌ | Локальная разработка, файл с правами 0o600 |
| `KeyringSecretProvider` | Системный Keyring | ✅ | Десктоп/сервер с доступным keyring-демоном (macOS, Gnome, KDE) |

`keyring_provider` оставлен в кодовой базе, но по умолчанию не используется — на headless-системах keyring часто недоступен.

### ChainSecretProvider

Объединяет несколько провайдеров в цепочку:
- **При чтении:** первый не-`None` результат (env_vars перезаписывает env_file)
- **При записи:** пишет только в провайдеры с `writable=True`

```python
# Порядок: env vars приоритетнее .env файла; keyring пока не используется
# При записи пишет в env_vars и keyring, но НЕ в .env файл
provider = ChainSecretProvider([
    EnvVarsSecretProvider(),           # writable=True
    EnvFileSecretProvider(env_file),   # writable=False (не пишем plaintext на диск)
    KeyringSecretProvider(),           # writable=True — оставлен, но не в цепочке по умолчанию
])
```

**По умолчанию (без keyring):**
```python
provider = ChainSecretProvider([
    EnvVarsSecretProvider(),
    EnvFileSecretProvider(env_file),
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

Приоритет: `EnvVarsSecretProvider` > `EnvFileSecretProvider` > Keyring.

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

## 9. ExportHistory — на каждый чат свой файл

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

## 10. Вывод и прогресс

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

## 11. Обработка ошибок и edge cases

### Сетевые сбои (п.15)
- retry с экспоненциальной задержкой для сетевых операций (настраивается в конфиге `retry.*`)
- Атомарная запись медиафайлов: tmp → fsync → rename
- Периодическое сохранение прогресса в `export_history.json` каждые 1000 сообщений
- При обрыве — `--resume` продолжает с последнего чекпоинта

### Нехватка места на диске (п.16)
- Перед экспортом — проверка `shutil.disk_usage()` в export-директории
- В процессе — проверка после каждых 50 медиафайлов
- При <100 MB свободно — остановка с ошибкой: «Недостаточно места на диске (осталось X MB)»
- Прогресс сохраняется для `--resume`

### Конфликты параметров (п.17-18)
- `--date-from`/`--date-to` и `--days` — взаимоисключающие (Click `cls=MutuallyExclusiveOption`)
- `--last N` и любые фильтры по дате — взаимоисключающие
- `--transcribe` без `--download-media` — предупреждение (транскрипция требует скачивания)
- Все конфликты — понятная ошибка, а не молчаливое игнорирование

### Прерванный экспорт (п.19)
- **JSON:** пишется атомарно (tmp → rename), при Ctrl+C остаётся валидный partial результат
- **Markdown:** файлы дописываются с маркером `<!-- export in progress -->`, убирается при завершении
- При Ctrl+C — `export_history.json` сохраняется с флагом `"interrupted": true`
- Следующий запуск с `--resume` продолжает с последнего сообщения

### Удалённый/заблокированный чат (п.20)
- Обработка `ChatNotFound`, `ChannelPrivate` — понятная ошибка пользователю
- В `export_history.json` сохраняется статус: `"status": "unavailable"`
- При `export --all --skip-unavailable` — пропуск недоступных чатов с предупреждением в лог
- При инкрементальном экспорте в недоступный чат — ошибка сразу, без попытки iter_messages

### Безопасность файлов

Права на чувствительные файлы:
- **Конфиг** (`cli_config.yaml`) — `0o600` на Unix
- **`.env` файл** — `0o600` на Unix
- **Экспорт-директория** — `0o700` на Unix
- **Windows:** restricted ACL через `win32security` (только текущий пользователь)
- В коде — хелпер `secure_permissions(path)`, платформозависимый
- При создании файла/директории — сразу выставлять права, до записи содержимого

## 12. Конфигурация CLI

Файл `~/.tg_exporter/cli_config.yaml`:

```yaml
# Версия конфига
version: 1

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

# Устойчивость к сбоям
retry:
  max_attempts: 3        # Попыток при сетевой ошибке
  delay_seconds: 2       # Начальная задержка (экспоненциальный backoff)
  max_delay_seconds: 60  # Максимальная задержка

# Rate limiting
rate_limit:
  media_download_delay_ms: 500   # Пауза между скачиваниями медиа
  message_fetch_delay_ms: 100    # Пауза между запросами сообщений
```

## 13. Миграция с десктопного приложения

### Что остаётся и дорабатывается

| Модуль | Что изменится |
|--------|---------------|
| `core/client_interface.py` | **НОВОЕ** — ABC для Telegram-клиента |
| `core/telethon_adapter.py` | **НОВОЕ** — реальная реализация (выделяется из `client.py`) |
| `core/auth/` | Адаптировать под `TelegramClientInterface` |
| `core/converter.py` | Без изменений |
| `core/orchestrator.py` | Адаптировать под `TelegramClientInterface` |
| `exporters/` | Без изменений |
| `services/` | `ExportHistory` — доработать хранение в папке чата |
| `models/` | Без изменений |
| `utils/cancellation.py` | Без изменений |
| `utils/logger.py` | Без изменений |

### Что удаляется полностью

| Модуль | Причина |
|--------|---------|
| `tg_exporter/ui/` (весь пакет) | Десктопный UI больше не нужен |
| `tg_exporter/utils/worker.py` | BackgroundWorker + EventDispatcher (только для GUI) |
| `main.py` | Старая точка входа в GUI-приложение |
| `tg_exporter/core/client.py` | Заменён на `client_interface.py` + `telethon_adapter.py` |
| `tg_exporter/core/credentials.py` | Адаптирован под `SecretProvider`, старый API удалён |
| `tg_exporter/core/profiles/` | Перенесён в CLI или удалён (профили управляются через `tg-exporter profile`) |

### Что создаётся заново

| Модуль | Описание |
|--------|----------|
| `tg_exporter_cli/` | CLI-приложение (весь пакет) |
| `tg_exporter_cli/container.py` | DI-контейнер |
| `tg_exporter_cli/secrets/` | SecretProvider, EnvProvider, KeyringProvider, ChainProvider |
| `tests/` | Полный тестовый набор |
| `tests/fakes/fake_telegram_client.py` | Фейковый клиент для тестов |
| `tests/fakes/factories.py` | Фабрики тестовых данных |

## 14. Фазы реализации

### Фаза 1: Абстракция клиента и базовая инфраструктура

- [ ] Создать `TelegramClientInterface` (ABC)
- [ ] Выделить `TelethonClientAdapter` из `client.py`
- [ ] Адаптировать `AuthService` и `ExportOrchestrator` под интерфейс
- [ ] Создать `tests/fakes/fake_telegram_client.py` и `factories.py`
- [ ] Установить `click`, `pyyaml`, `python-dotenv`
- [ ] Создать `tg_exporter_cli/secrets/`
- [ ] Создать `tg_exporter_cli/container.py`
- [ ] Создать `tg_exporter_cli/main.py`

### Фаза 2: Команды и тесты (MVP)

- [ ] Реализовать `auth login` / `auth status` / `auth logout`
- [ ] Реализовать `export` (--chat, --output, --format, --last N)
- [ ] Написать unit-тесты: Converter, ExportHistory, Exporters, SecretProvider
- [ ] Написать integration-тесты: `test_export_command.py`, `test_auth_command.py`
- [ ] Проверить сквозной сценарий на фейковом клиенте

### Фаза 3: Полноценный экспорт и чаты

- [ ] Добавить все опции экспорта (фильтры, медиа, транскрипция, аналитика)
- [ ] Реализовать `--days N`
- [ ] Доработать `ExportHistory` — хранение в папке чата
- [ ] Реализовать `chats list` / `show` / `add` / `remove`
- [ ] Написать тесты для всех опций export, команды chats
- [ ] Прогресс-бар в консоли

### Фаза 4: Конфигурация, профили и удаление десктопа

- [ ] Создать модель `CliConfig` (YAML)
- [ ] Реализовать `config show/set`
- [ ] Реализовать `profile list/add/remove/switch`
- [ ] Написать тесты: `test_config_command.py`, `test_profile_command.py`
- [ ] Удалить `tg_exporter/ui/`, `utils/worker.py`, `main.py`, `client.py`
- [ ] Обновить `pyproject.toml`, убрать `customtkinter` из зависимостей

### Фаза 5: CI/CD и пакетирование

- [ ] Обновить `pyproject.toml` с entry point `tg-exporter`
- [ ] Добавить `pytest` в CI (запуск на каждом PR)
- [ ] Обновить CI для сборки CLI (PyPI package, single binary?)
- [ ] Документировать интеграцию с cron/systemd timer
- [ ] Обновить README

## 15. Пример использования

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

## 16. Риски и ограничения

| Риск | Митигация |
|------|-----------|
| Keyring в headless-окружении | SecretProvider с fallback на .env файл |
| Интерактивный ввод кода при первом логине | CI/CD-friendly: только если сессия уже сохранена через `auth login` |
| Долгий экспорт больших каналов | `--last N` для тестирования, прогресс-бар |
| Разные часовые пояса | Все даты в ISO 8601 с timezone |
| Расхождение фейкового и реального клиента | `TelegramClientInterface` — контракт; обе реализации проходят один набор тестов |

## 17. Зависимости

```
# CLI и конфигурация
click>=8.1,<9.0
pyyaml>=6.0,<7.0
python-dotenv>=1.0,<2.0
rich>=13.0

# Telegram API
telethon

# Хранение секретов
keyring

# Транскрипция (опционально)
faster-whisper
imageio-ffmpeg

# Тестирование
pytest>=8.0
pytest-asyncio       # для async-тестов с Telethon
pytest-cov           # coverage
```

**Удаляются из `requirements.txt`:**
- `customtkinter` — десктопный UI больше не нужен
- `PySocks` — если не используется для прокси (проверить)
