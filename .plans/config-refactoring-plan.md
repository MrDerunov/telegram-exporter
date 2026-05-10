# План переделки системы конфигов и секретов

## Цель

Разделить текущую смешанную систему конфигов (`CliConfig` + `AppConfig` + `SecretProvider`
+ `ProfileManager` со своим файлом) на три чётко разделённые части:

1. **Static config** — настройки запуска (config.json + .env + env vars + defaults)
2. **Runtime state** — состояние приложения (state.json: профили, чаты, активный телефон)
3. **Secrets** — токены/ключи (keyring или secrets.json)

---

## Текущее состояние (проблемы)

| Что | Где хранится | Проблема |
|---|---|---|
| Статические настройки | `~/.tg-exporter/cli_config.yaml` | Жёсткий путь, нет переопределения через env |
| Состояние (чаты) | Внутри `cli_config.yaml` | Смешано с настройками |
| Состояние (профили) | `~/.tg-exporter/profiles.json` | Отдельный файл, свой код I/O |
| Секреты | `SecretProvider` chain (env vars → .env) | Keyring не в цепочке по умолчанию |
| Лог | `~/.tg-exporter/app.log` | Жёсткий путь |
| AppConfig (legacy) | `~/.tg-exporter/config.json` | Дублирует CliConfig, устаревший формат |

---

## Шаг 1. Новые абстракции и типы данных

### 1.1. Статические настройки: `StaticConfig`

**Новый файл:** `tg_exporter/hosting/static_config.py`

Frozen dataclass, все поля со значениями по умолчанию (= code defaults):

```python
@dataclass(frozen=True)
class StaticConfig:
    version: int = 1
    api_id: str = ""
    api_hash: str = ""              # из секретов при мердже
    deepgram_api_key: str = ""      # из секретов при мердже

    # Транскрипция
    transcription_provider: str = "local"
    transcription_model: str = "base"
    transcription_language: str = "multi"

    # Экспорт по умолчанию
    default_format: str = "both"
    default_words_per_file: int = 50000
    default_download_media: bool = False
    default_transcribe: bool = False
    default_analytics: bool = False
    include_private_chats: bool = False
    default_profile: str = "default"

    # Markdown
    markdown: MarkdownSettings = field(default_factory=MarkdownSettings)

    # Источник секретов: "keyring" или "file"
    secrets_source: str = "keyring"

    # Логирование
    log_level: str = "INFO"

    # Retry
    retry_max_attempts: int = 3
    retry_delay_seconds: int = 2
    retry_max_delay_seconds: int = 60

    # Rate limit
    rate_limit_media_download_delay_ms: int = 500
    rate_limit_message_fetch_delay_ms: int = 100
```

Методы:
- `from_raw(data: dict) -> StaticConfig` — собирает из словаря (плоского или вложенного), аналогично текущему `CliConfig.from_raw()`
- `to_dict() -> dict` — для отладки/показа

**Заменяет:**
- `tg_exporter/hosting/app_config.py:AppConfig`
- Поля статических настроек из `tg_exporter_cli/hosting/cli_config.py:CliConfig`

### 1.2. Состояние: `StateModel`

**Новый файл:** `tg_exporter/hosting/state_model.py`

```python
@dataclass(frozen=True)
class ProfileEntry:
    phone: str
    display_name: str = ""
    api_id: str = ""

@dataclass(frozen=True)
class ChatEntry:
    name: str
    id: int

@dataclass(frozen=True)
class StateModel:
    active_phone: str = ""
    profiles: tuple[ProfileEntry, ...] = field(default_factory=tuple)
    chats: tuple[ChatEntry, ...] = field(default_factory=tuple)
```

Методы:
- `from_dict(data: dict) -> StateModel`
- `to_dict() -> dict`

**Заменяет:**
- Поля состояния из `CliConfig` (chats, default_profile/active_phone)
- Модель `Profile` из `tg_exporter/telegram/profiles/profile.py` (переиспользуем `ProfileEntry`)

### 1.3. Интерфейс хранилища состояния: `ISettingsStore`

**Новый файл:** `tg_exporter/hosting/settings_store.py`

```python
class ISettingsStore(ABC):
    @abstractmethod
    def load(self) -> StateModel: ...
    @abstractmethod
    def save(self, state: StateModel) -> None: ...
```

### 1.4. Интерфейс хранилища секретов: `ISecretStore`

**Новый файл:** `tg_exporter/secrets/secret_store.py`

```python
class ISecretStore(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[str]: ...
    @abstractmethod
    def set(self, key: str, value: str) -> None: ...
    @abstractmethod
    def delete(self, key: str) -> None: ...
```

Аналогичен текущему `SecretProvider`, но чётко разделён:
- Больше нет `writable` флага (все хранилища writable)
- Больше нет цепочек (мердж делает ConfigurationProvider)

**Заменяет:** `tg_exporter/secrets/secret_provider.py:SecretProvider`

---

## Шаг 2. Реализации хранилищ

### 2.1. JsonSettingsStore

**Новый файл:** `tg_exporter/hosting/json_settings_store.py`

```python
class JsonSettingsStore(ISettingsStore):
    def __init__(self, config_dir: Path) -> None:
        self._path = config_dir / "state.json"

    def load(self) -> StateModel:
        # читает из state.json, при ошибке возвращает StateModel()

    def save(self, state: StateModel) -> None:
        # атомарная запись + secure_permissions (0o600)
```

> **Примечание:** `config_dir` берётся из `ConfigurationResult.config_dir` при создании
> в хосте, а не через DI. Это позволяет тестам подменять путь.

### 2.2. KeyringSecretStore

**Новый файл:** `tg_exporter/secrets/keyring_secret_store.py`

```python
class KeyringSecretStore(ISecretStore):
    def get(self, key: str) -> Optional[str]: ...
    def set(self, key: str, value: str) -> None: ...
    def delete(self, key: str) -> None: ...
```

Переносит логику из `tg_exporter/secrets/keyring_secret_provider.py`.

### 2.3. JsonSecretStore

**Новый файл:** `tg_exporter/secrets/json_secret_store.py`

```python
class JsonSecretStore(ISecretStore):
    def __init__(self, config_dir: Path) -> None:
        self._path = config_dir / "secrets.json"

    def get(self, key: str) -> Optional[str]: ...
    def set(self, key: str, value: str) -> None: ...
    def delete(self, key: str) -> None: ...
```

Write — атомарная запись + `secure_permissions(0o600)`.
Read — парсит JSON, кеширует в памяти, перечитывает при изменении.

---

## Шаг 3. ConfigurationProvider — чтение и мердж всех источников

**Новый файл:** `tg_exporter/hosting/configuration_provider.py`

### 3.1. Определение config_dir

```python
def resolve_config_dir() -> Path:
    # 1. TELEGRAM_EXPORTER_CONFIG_DIR (переменная среды)
    env_dir = os.environ.get("TELEGRAM_EXPORTER_CONFIG_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    # 2. ./ (текущая рабочая директория)
    return Path.cwd()
```

### 3.2. build_merged_config()

```python
def build_merged_config(config_dir: Path, env_file: Path | None = None) -> dict:
    """
    Порядок источников (последующий переопределяет предыдущий):
    1. Code defaults (значения StaticConfig по умолчанию, как dict)
    2. config.json (config_dir / "config.json")
    3. state.json (config_dir / "state.json", если есть)
    4. secrets.json (config_dir / "secrets.json", если есть)
    5. .env файл (config_dir / ".env")
    6. Env vars (os.environ, с префиксом TG_EXPORTER_ или без)

    Правило: пустое значение (None, "") НЕ переопределяет непустое.
    """
```

**Структура config.json (пример):**
```json
{
  "version": 1,
  "api_id": "12345",
  "transcription": {
    "provider": "local",
    "model": "base",
    "language": "multi"
  },
  "defaults": {
    "format": "both",
    "words_per_file": 50000,
    "download_media": false,
    "transcribe": false,
    "analytics": false
  },
  "secrets_source": "keyring",
  "logging": {
    "level": "INFO"
  },
  "retry": {
    "max_attempts": 3,
    "delay_seconds": 2,
    "max_delay_seconds": 60
  },
  "rate_limit": {
    "media_download_delay_ms": 500,
    "message_fetch_delay_ms": 100
  }
}
```

**Структура state.json (пример):**
```json
{
  "active_phone": "+79991234567",
  "profiles": [
    {"phone": "+79991234567", "display_name": "Sergey", "api_id": "12345"}
  ],
  "chats": [
    {"name": "Друзья", "id": 123456789}
  ]
}
```

**Мердж с учётом «не переопределять пустым»:**
```python
def _merge_dicts(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _merge_dicts(base[key], value)
        elif value not in (None, "", 0):  # 0 может быть валидным api_id
            base[key] = value
    return base
```

### 3.3. Класс ConfigurationProvider

**Важно — разделение ответственности:**
`ConfigurationProvider` НЕ маппит словарь в типы. Он только собирает сырые данные
из всех источников и возвращает `ConfigurationResult` с сырым словарём.
Маппингом в `StaticConfig` / `StateModel` занимается **хост** (`CliHost._bind_services`).

```python
class ConfigurationProvider:
    def __init__(self, config_dir: Path, env_file: Path | None = None):
        self._config_dir = config_dir
        self._env_file = env_file

    def build(self) -> ConfigurationResult:
        merged = build_merged_config(self._config_dir, self._env_file)
        return ConfigurationResult(
            raw=merged,
            config_dir=self._config_dir,
        )

@dataclass(frozen=True)
class ConfigurationResult:
    """Сырой результат сборки конфигурации из всех источников.
    Хост маппит raw в типизированные конфиги при _bind_services.
    Регистрируется в DI как singleton — любой компонент может получить
    доступ к config_dir или сырым данным.
    """
    raw: dict          # объединённый словарь всех настроек
    config_dir: Path   # директория, где лежат config/state/secrets файлы
```

---

## Шаг 4. Переработка CliHost

**Файл:** `tg_exporter_cli/hosting/cli_host.py`

### 4.1. Разделение build() и run()

- **`build()`** — только собирает конфигурацию и регистрирует зависимости в DI.
  Не создаёт файлов/папок, не делает операций с ОС.
- **`run()`** — инициализирует логгер (создаёт app.log), может выполнять другие
  операции с ОС (создание директорий, миграции и т.п.).

```python
class CliHost:
    def build(self) -> CliHost:
        # 1. Определить config_dir
        config_dir = resolve_config_dir()

        # 2. Собрать конфигурацию из всех источников (только чтение, без записи)
        provider = ConfigurationProvider(config_dir, self._env_file)
        result = provider.build()

        # 3. Зарегистрировать зависимости в DI
        self._bind_services(result)
        return self

    def run(self) -> None:
        """Инициализация ОС-ресурсов: логгер, директории и т.п.
        Вызывается ПОСЛЕ build() при старте приложения."""
        result = self._container.get(ConfigurationResult)
        init_logger(result.config_dir)
```

### 4.2. Сигнатура _bind_services — принимает ConfigurationResult

Хост сам маппит `ConfigurationResult.raw` в типизированные конфиги.
Это разделение ответственности: ConfigurationProvider собирает сырые данные,
хост превращает их в типы.

```python
def _bind_services(self, result: ConfigurationResult) -> None:
    c = self._container

    # ConfigurationResult — регистрируем как есть, для доступа к config_dir
    c.register_instance(ConfigurationResult, result)

    # Маппинг сырого словаря в типизированные конфиги (делает хост)
    static_config = StaticConfig.from_raw(result.raw)
    state_model = StateModel.from_dict(result.raw)

    c.register_instance(StaticConfig, static_config)
    c.register_instance(StateModel, state_model)

    # SecretStore — тип выбирается на основе настройки из static_config
    if static_config.secrets_source == "file":
        secret_store = JsonSecretStore(result.config_dir)
    else:
        secret_store = KeyringSecretStore()
    c.register_instance(ISecretStore, secret_store)

    # SettingsStore
    settings_store = JsonSettingsStore(result.config_dir)
    c.register_instance(ISettingsStore, settings_store)

    # ProfileManager — принимает ISecretStore + ISettingsStore
    c.register(
        ProfileManager,
        lambda ctr: ProfileManager(
            secrets=ctr.get(ISecretStore),
            settings=ctr.get(ISettingsStore),
        ),
    )

    # TelegramClientManager
    c.register(
        ITelegramClientManager,
        lambda ctr: TelethonClientManager(
            config=ctr.get(StaticConfig),
            secrets=ctr.get(ISecretStore),
        ),
    )

    # Остальное без изменений
    c.register(AuthService, lambda ctr: AuthService(ctr.get(ITelegramClientManager)))
    c.register(ExportHistory, lambda _: ExportHistory())
    c.register(
        ExportOrchestrator,
        lambda ctr: ExportOrchestrator(
            ctr.get(ITelegramClientManager),
            ctr.get(StaticConfig),
            ctr.get(ExportHistory),
        ),
    )
```

### 4.3. Переход на ISecretStore — без обратной совместимости

**Вариант C:** Обновить все команды сразу на `ISecretStore`.
Никаких алиасов `SecretProvider` — старый интерфейс удаляется полностью.
Все команды, использующие `host.get(SecretProvider)`, переходят на `host.get(ISecretStore)`.

### 4.4. rebind_services — callback принимает ConfigurationResult

```python
def rebind_services(self, callback: Callable[[Container, ConfigurationResult], None]) -> CliHost:
    """Позволяет переопределить регистрации сервисов (для тестов).
    callback получает (container, ConfigurationResult).
    Замена старого callback(container, raw_config) — теперь передаём типизированный объект."""
    result = self._container.get(ConfigurationResult)
    callback(self._container, result)
    return self
```

### 4.5. Доступ к config_dir из команд

Команды, которым нужен путь к конфиг-директории, получают его через DI:
```python
result = host.get(ConfigurationResult)
config_dir = result.config_dir
```

Больше нет `host.config_path` — путь к директории конфига доступен через
`ConfigurationResult`, который зарегистрирован в DI как singleton.

---

## Шаг 5. Обновление ProfileManager

**Файл:** `tg_exporter/telegram/profiles/profile_manager.py`

### 5.1. Новый конструктор

```python
class ProfileManager:
    def __init__(self, secrets: ISecretStore, settings: ISettingsStore):
        self._secrets = secrets
        self._settings = settings
        ...

    def _load(self):
        state = self._settings.load()
        self._profiles = [
            Profile(phone=p.phone, display_name=p.display_name, api_id=p.api_id)
            for p in state.profiles
        ]
        self._active_phone = state.active_phone

    def _save(self):
        state = StateModel(
            active_phone=self._active_phone,
            profiles=tuple(
                ProfileEntry(phone=p.phone, display_name=p.display_name, api_id=p.api_id)
                for p in self._profiles
            ),
            chats=...,  # чаты теперь в StateModel, но не трогаем их здесь
        )
        self._settings.save(state)
```

### 5.2. Проблема: чаты в StateModel

Сейчас чаты управляются командами `chats add/remove` через `CliConfig.chats` и
сохраняются через `save_cli_config()`.

После рефакторинга чаты должны быть в `StateModel.chats`. Команды `chats`
должны использовать `ISettingsStore` для сохранения.

**Решение:** `ProfileManager._save()` сохраняет ТОЛЬКО профили (не трогает чаты).
При сохранении читает текущее состояние через `ISettingsStore.load()`,
меняет в нём только профили и `active_phone`, а `chats` оставляет как есть.
Команды чатов работают с `ISettingsStore` напрямую, загружая полный `StateModel`,
меняя в нём `chats`, и сохраняя обратно.

### 5.3. Модель Profile

`tg_exporter/telegram/profiles/profile.py` — оставить для внутреннего
использования в `ProfileManager`. `ProfileEntry` в `state_model.py` —
это DTO для сериализации.

---

## Шаг 6. Обновление логгера

**Файл:** `tg_exporter/utils/logger.py`

Сейчас `LOG_PATH = Path(os.path.expanduser("~/.tg-exporter/app.log"))`.

Нужно:
- Добавить функцию `init_logger(config_dir: Path)`:
  ```python
  def init_logger(config_dir: Path) -> None:
      global LOG_PATH, logger
      LOG_PATH = config_dir / "app.log"
      logger = AppLogger(LOG_PATH)
  ```
- При инициализации `AppLogger.__init__` использовать `LOG_PATH` из глобальной переменной.
- Вызывать `init_logger()` из `CliHost.run()` — именно run() отвечает за создание файлов/папок в ОС, build() только регистрирует зависимости.

---

## Шаг 7. Обновление команд CLI

### 7.1. Команда `chats`

**Файл:** `tg_exporter_cli/commands/chats.py`

Изменения:
- `host.get(CliConfig)` → `host.get(StateModel)` (для чтения chats)
- `save_cli_config(...)` → `host.get(ISettingsStore).save(new_state)`
- `host.config_path` → больше не нужен для сохранения

### 7.2. Команда `config`

**Файл:** `tg_exporter_cli/commands/config_cmd.py`

Изменения:
- `host.get(CliConfig)` → `host.get(StaticConfig)`
- `save_cli_config(...)` → запись через `ISettingsStore` или прямую запись config.json
- `host.config_path` → `host.get(ConfigurationResult).config_dir`

### 7.3. Команда `profile`

**Файл:** `tg_exporter_cli/commands/profile.py`

Изменения:
- `host.get(CliConfig)` → больше не нужно (default_profile теперь в StateModel/ProfileManager)
- `save_cli_config(...)` → убрать, `ProfileManager` сам сохраняет через ISettingsStore
- `host.config_path` → `host.get(ConfigurationResult).config_dir` (если нужен для информации)

### 7.4. Команда `auth`

**Файл:** `tg_exporter_cli/commands/auth.py`

Изменения:
- `host.get(SecretProvider)` → `host.get(ISecretStore)`
- `host.get(CliConfig)` → `host.get(StaticConfig)`

### 7.5. Команда `doctor`

**Файл:** `tg_exporter_cli/commands/doctor.py`

Изменения:
- `DEFAULT_CONFIG_DIR` → `host.get_config_dir()` или `resolve_config_dir()`
- Проверять наличие `config.json`, `state.json`, `secrets.json` в config_dir

---

## Шаг 8. Обновление core-сервисов

### 8.1. TelethonClientManager

**Файл:** `tg_exporter/telegram/telegram_client_manager.py`

Изменения:
- `AppConfig` → `StaticConfig` (в импортах и конструкторе)
- `SecretProvider` → `ISecretStore` (в импортах и конструкторе)

### 8.2. ExportOrchestrator

**Файл:** `tg_exporter/services/export/export_orchestrator.py`

Изменения:
- `AppConfig` → `StaticConfig` (в импортах)

### 8.3. AuthService

**Файл:** `tg_exporter/telegram/auth/auth_service.py`

Без изменений (не зависит от AppConfig/SecretProvider напрямую).

---

## Шаг 9. Удаление старых файлов

| Файл | Заменён на |
|---|---|
| `tg_exporter_cli/hosting/cli_config.py` | `StaticConfig` + `StateModel` |
| `tg_exporter_cli/hosting/cli_config_repository.py` | `ISettingsStore` + `JsonSettingsStore` |
| `tg_exporter_cli/hosting/config_mapper.py` | Хост маппит в `_bind_services` |
| `tg_exporter/hosting/app_config.py` | `StaticConfig` |
| `tg_exporter/hosting/app_config_repository.py` | `ConfigurationProvider` |
| `tg_exporter/hosting/app_config_validator.py` | Валидация в `StaticConfig.from_raw()` |
| `tg_exporter/secrets/secret_provider.py` | `ISecretStore` |
| `tg_exporter/secrets/chain_secret_provider.py` | Не нужен (мердж делает ConfigurationProvider) |
| `tg_exporter/secrets/env_vars_secret_provider.py` | Чтение env vars в ConfigurationProvider |
| `tg_exporter/secrets/env_file_secret_provider.py` | Чтение .env в ConfigurationProvider |
| `tg_exporter/telegram/credentials_manager.py` | `KeyringSecretStore` |

### Оставить как есть:

| Файл | Причина |
|---|---|
| `tg_exporter/secrets/secret_keys.py` | Константы ключей нужны всем |
| `tg_exporter/secrets/keyring_secret_provider.py` | `KeyringSecretStore` |
| `tg_exporter/telegram/profiles/profile.py` | Внутренняя модель ProfileManager |
| `tg_exporter_cli/hosting/container.py` | DI-контейнер без изменений |
| `tg_exporter_cli/hosting/__init__.py` | Точка входа get_host() |

---

## Шаг 10. Обновление DI-регистраций

### 10.1. Новые типы в контейнере

| Тип | Реализация | Жизненный цикл |
|---|---|---|
| `ConfigurationResult` | instance (сырой словарь + config_dir) | singleton |
| `StaticConfig` | instance (маппится хостом из result.raw) | singleton |
| `StateModel` | instance (маппится хостом из result.raw) | singleton |
| `ISettingsStore` | `JsonSettingsStore` | singleton |
| `ISecretStore` | `KeyringSecretStore` / `JsonSecretStore` | singleton |

### 10.2. Доступ к config_dir

Любой компонент получает config_dir через DI:
```python
result = container.get(ConfigurationResult)
config_dir = result.config_dir
```

Больше нет `host.config_path` — путь доступен через `ConfigurationResult.config_dir`.

---

## Шаг 11. Обновление тестов

### 11.1. Новые fakes

- `FakeSettingsStore` — реализует `ISettingsStore` в памяти
- `FakeSecretStore` — реализует `ISecretStore` в памяти (уже есть похожее в тестах)

### 11.2. Обновление существующих тестов

- `test_models.py` — обновить импорты (CliConfig → StaticConfig, StateModel)
- `test_profiles.py` — ProfileManager теперь принимает ISettingsStore
- `test_chain_secret_provider.py` — удалить
- `test_env_file_secret_provider.py` — удалить
- `test_env_vars_secret_provider.py` — удалить
- `test_keyring_secret_provider.py` — переименовать в test_keyring_secret_store

---

---

## Порядок выполнения (фазы)

### Фаза 1: Новые типы и интерфейсы (no-op, только добавляем)
- [ ] 1.1 `tg_exporter/hosting/static_config.py` — StaticConfig
- [ ] 1.2 `tg_exporter/hosting/state_model.py` — StateModel, ProfileEntry, ChatEntry
- [ ] 1.3 `tg_exporter/hosting/settings_store.py` — ISettingsStore ABC
- [ ] 1.4 `tg_exporter/secrets/secret_store.py` — ISecretStore ABC

### Фаза 2: Реализации хранилищ
- [ ] 2.1 `tg_exporter/hosting/json_settings_store.py` — JsonSettingsStore
- [ ] 2.2 `tg_exporter/secrets/keyring_secret_store.py` — KeyringSecretStore
- [ ] 2.3 `tg_exporter/secrets/json_secret_store.py` — JsonSecretStore

### Фаза 3: ConfigurationProvider
- [ ] 3.1 `tg_exporter/hosting/configuration_provider.py` — resolve_config_dir, build_merged_config, map_merged_to_typed

### Фаза 4: Обновление CliHost
- [ ] 4.1 Переписать `build()` с новыми компонентами
- [ ] 4.2 Обновить `_bind_services()` с новыми регистрациями
- [ ] 4.3 Добавить обратную совместимость для SecretProvider

### Фаза 5: Обновление ProfileManager и логгера
- [ ] 5.1 `profile_manager.py` — принимать ISettingsStore, сохранять в state.json
- [ ] 5.2 `logger.py` — init_logger(config_dir)

### Фаза 6: Обновление core-сервисов
- [ ] 6.1 `telegram_client_manager.py` — AppConfig → StaticConfig, SecretProvider → ISecretStore
- [ ] 6.2 `export_orchestrator.py` — AppConfig → StaticConfig

### Фаза 7: Обновление CLI-команд
- [ ] 7.1 `chats.py` — CliConfig → StateModel + ISettingsStore
- [ ] 7.2 `config_cmd.py` — CliConfig → StaticConfig
- [ ] 7.3 `profile.py` — CliConfig → StateModel/ISettingsStore
- [ ] 7.4 `auth.py` — CliConfig → StaticConfig, SecretProvider → ISecretStore
- [ ] 7.5 `doctor.py` — обновить проверяемые пути

### Фаза 8: Удаление старого кода
- [ ] 8.1 Удалить файлы из списка в шаге 9
- [ ] 8.2 Обновить `__init__.py` в затронутых пакетах
- [ ] 8.3 Обновить импорты во всех файлах

### Фаза 9: Обновление тестов
- [ ] 9.1 Новые fakes (FakeSettingsStore, FakeSecretStore)
- [ ] 9.2 Обновить существующие тесты
- [ ] 9.3 Запустить полный тестовый набор



---

## Заметки

- **Config dir определяет всё:** config.json, state.json, secrets.json, .env, app.log
  живут в одной директории, определяемой через `TELEGRAM_EXPORTER_CONFIG_DIR` или `./`.
  Больше никаких `~/.tg-exporter/`.

- **Пустые значения не переопределяют:** при мердже словарей `""`, `None`, пустой
  список не затирают существующее значение из источника с более низким приоритетом.
  Исключение: явный `false` для булевых полей — валидное значение, должно переопределять.

- **SecretStore по умолчанию keyring:** для ручного использования на ПК.
  `secrets_source: "file"` — для CI, пишет в `secrets.json`.

- **Без обратной совместимости:** `SecretProvider` удаляется полностью, все команды
  переходят на `ISecretStore`. `CliConfig` удаляется (все поля переносятся
  в `StaticConfig` + `StateModel`).

- **API_ID не секрет:** хранится в config.json как обычное поле static config.

- **Сессии профилей:** ключ `{api_id}:session:{phone}`, как и сейчас в `_session_key()`.
