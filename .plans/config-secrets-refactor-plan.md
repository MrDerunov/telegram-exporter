# План: Рефакторинг конфигурации и секретов

## Цель

Унифицировать загрузку конфигурации и секретов: единая точка входа, единый словарь → типизированные объекты.
Секреты и настройки больше не разбросаны по `SecretProvider` в командах, `CredentialsManager`, разным репозиториям.

## Текущие проблемы

1. **Разбросанные источники секретов**: `api_hash` читается в `auth.py` через `secret_provider.get("TG_EXPORTER_API_HASH")`, в `TelethonClientManager` через `CredentialsManager.load_api_hash()`. Нет единой точки.
2. **SecretProvider зарегистрирован в DI и дёргается напрямую из команд** — нарушение слоёв.
3. **CredentialsManager** — устаревший класс (будет удалён), но всё ещё используется в `TelethonClientManager`, `ProfileManager`.
4. **Нет единой точки сбора** всех настроек перед регистрацией сервисов — `build()` смешивает чтение конфига и DI-регистрацию.

## Целевая архитектура

```
CliHost.build()
  ├── _configure_cli() → dict
  │     • ChainSecretProvider([EnvVars, EnvFile])
  │     • YAML-конфиг через load_cli_config()
  │     • Чтение секретов из SecretProvider
  │     • Мёрж в единый словарь
  │
  └── _bind_services(raw_config: dict) → None
        • raw_config → CliConfig.from_raw(raw_config)   (frozen)
        • CliConfig → AppConfig через config_mapper       (frozen)
        • Регистрация SecretProvider, CliConfig, AppConfig в DI
        • Регистрация всех сервисов
```

### Ключевые правила

- **CredentialsManager не используется.** Удаляется из нового кода. Сам файл пока остаётся (будет удалён отдельно).
- **SecretProvider регистрируется в DI.** Сервисы используют его для `set()`/`delete()` — сохранение/загрузка сессий.
- **Цепочка секретов:** `EnvVarsSecretProvider` → `EnvFileSecretProvider`. Keyring не в цепочке.
- **Mapper CliConfig → AppConfig** — отдельная функция/объект (не метод CliConfig).
- **Auth** может работать с `secret_provider` напрямую.
- **api_hash** остаётся в `CliConfig` и `AppConfig`.
- **Префикс `TG_EXPORTER_`** — все ключи секретов в env/файлах используют этот префикс во избежание коллизий.
- **Конфиги readonly (frozen).** `CliConfig` и `AppConfig` становятся frozen dataclass. Изменение настроек — через `secret_provider.set()` с последующей перестройкой через `dataclasses.replace()`.
- **`rebind_services(callback)`** — callback принимает `(container, raw_config)` для возможности переопределения конфигурации в тестах.

---

## Шаг 1. CliHost — разделение build() на _configure_cli + _bind_services

**Файл: `tg_exporter_cli/hosting/cli_host.py`**

### _configure_cli(self) -> dict

1. Создаёт цепочку `ChainSecretProvider([EnvVarsSecretProvider(), EnvFileSecretProvider(self._env_file)])`
2. Сохраняет в `self._secret_provider` (для последующей регистрации в DI)
3. Загружает YAML-конфиг через `load_cli_config(self._config_path)` → приводит к словарю (все поля, кроме секретов)
4. Читает секреты из `self._secret_provider`:
   - `API_HASH` → ключ в провайдере (EnvVars добавит префикс `TG_EXPORTER_`)
   - `DEEPGRAM_API_KEY`
   - `SESSION`
5. Мёржит: `raw_config = {**yaml_dict, "api_hash": secrets.API_HASH, "deepgram_api_key": secrets.DEEPGRAM_API_KEY, "session": secrets.SESSION}`
6. Возвращает словарь

### _bind_services(self, raw_config: dict) -> None

1. Регистрирует `self._secret_provider` как `SecretProvider` в DI (`register_instance`)
2. `cli_config = CliConfig.from_raw(raw_config)` — маппинг словаря на frozen dataclass
3. `app_config = map_to_app_config(cli_config)` — отдельный config_mapper
4. Регистрирует `cli_config`, `app_config` в DI (`register_instance`)
5. Регистрирует остальные сервисы (без CredentialsManager):
   - `SecretProvider` — уже зарегистрирован
   - `ProfileManager(secret_provider)` — вместо `ProfileManager(credentials)`
   - `TelethonClientManager(app_config, secret_provider)` — вместо `(app_config, credentials)`
   - `ITelegramClientManager → TelethonClientManager`
   - `AuthService(ITelegramClientManager)`
   - `ExportHistory()`
   - `ExportOrchestrator(ITelegramClientManager, app_config, export_history)` — без `deepgram_key`

### rebind_services

```python
def rebind_services(self, callback: Callable[[Container, dict], None]) -> CliHost:
    """Позволяет переопределить регистрации сервисов (для тестов).
    callback получает (container, raw_config)."""
    callback(self._container, self._raw_config)
    return self
```

`self._raw_config` сохраняется как атрибут после `_configure_cli`.

---

## Шаг 2. CliConfig — frozen + from_raw

**Файл: `tg_exporter_cli/hosting/cli_config.py`**

- `@dataclass(frozen=True)` — конфиг становится иммутабельным
- Новые поля: `api_hash: str = ""`, `deepgram_api_key: str = ""`
- Новый метод: `@classmethod from_raw(data: dict) -> CliConfig` — собирает экземпляр из словаря (плоского или с вложенными ключами `defaults.*`, `transcription.*`, `retry.*`, `rate_limit.*`, `logging.*`)
- Для изменения значений — `dataclasses.replace(config, api_id="new_value")`
- `ChatEntry` — тоже frozen

---

## Шаг 3. config_mapper — отдельный mapper CliConfig → AppConfig

**Новый файл: `tg_exporter_cli/hosting/config_mapper.py`**

```python
def map_to_app_config(cli_config: CliConfig) -> AppConfig:
    """Маппит CliConfig на AppConfig, перенося все поля включая секреты."""
    return AppConfig(
        api_id=cli_config.api_id,
        api_hash=cli_config.api_hash,
        transcription_provider=cli_config.transcription_provider,
        transcription_language=cli_config.transcription_language,
        local_whisper_model=cli_config.transcription_model,
        deepgram_api_key=cli_config.deepgram_api_key,
        markdown=MarkdownSettings(words_per_file=cli_config.default_words_per_file),
    )
```

---

## Шаг 4. AppConfig — frozen + api_hash

**Файл: `tg_exporter/hosting/app_config.py`**

- `@dataclass(frozen=True)` — конфиг становится иммутабельным
- Добавить поле `api_hash: str = ""`
- `deepgram_api_key` — обычное поле (убрать особую логику исключения из `to_dict()`/`from_dict()`)
- `with_api_id()` остаётся (через `dataclasses.replace`)
- `to_dict()` / `from_dict()` — адаптировать под frozen (from_dict остаётся classmethod)

---

## Шаг 5. cli_config_repository — исключить секреты из YAML

**Файл: `tg_exporter_cli/hosting/cli_config_repository.py`**

- `load_cli_config()` — возвращает CliConfig без секретных полей (как сейчас)
- `save_cli_config()` — НЕ сериализует `api_hash`, `deepgram_api_key` (секреты не в YAML)
- При сохранении: секретные поля исключаются из словаря перед записью в YAML

---

## Шаг 6. Константы секретов и CLI-константы

### 6a. Константы ключей SecretProvider

**Новый файл: `tg_exporter/secrets/secret_keys.py`**

Все ключи, используемые с `SecretProvider`, определяются как константы в одном месте:

```python
# tg_exporter/secrets/secret_keys.py
"""Константы ключей для SecretProvider. Единый источник имён."""

# Префикс для переменных окружения и .env файлов
_ENV_PREFIX = "TG_EXPORTER_"

# Ключи секретов (без префикса — EnvVarsSecretProvider добавляет _ENV_PREFIX)
API_HASH = "API_HASH"
API_ID = "API_ID"
SESSION = "SESSION"
DEEPGRAM_API_KEY = "DEEPGRAM_API_KEY"

# Полные имена переменных окружения (с префиксом)
API_HASH_ENV = f"{_ENV_PREFIX}API_HASH"
API_ID_ENV = f"{_ENV_PREFIX}API_ID"
SESSION_ENV = f"{_ENV_PREFIX}SESSION"
DEEPGRAM_API_KEY_ENV = f"{_ENV_PREFIX}DEEPGRAM_API_KEY"
```

Использование в коде:
```python
from tg_exporter.secrets.secret_keys import API_HASH, SESSION, DEEPGRAM_API_KEY
secret_provider.get(API_HASH)
secret_provider.set(SESSION, session_str)
```

### 6b. CLI-константы

**Новый файл: `tg_exporter_cli/cli_constants.py`**

Константы, используемые только в консольном приложении:

```python
# tg_exporter_cli/cli_constants.py
"""Константы CLI-приложения."""
from pathlib import Path

# Директория и файлы конфигурации
CONFIG_DIR = Path.home() / ".tg_exporter"
CONFIG_FILENAME = "cli_config.yaml"
DEFAULT_ENV_FILENAME = ".env"
DEFAULT_SECRETS_ENV_FILENAME = "secrets.env"
```

Существующие константы из `cli_config.py` (`DEFAULT_CONFIG_DIR`, `DEFAULT_CONFIG_FILENAME`, `DEFAULT_ENV_FILENAME`, `DEFAULT_SECRETS_ENV_FILENAME`) переносятся в этот файл.

### 6c. Префикс секретов — согласование

**Файл: `tg_exporter/secrets/env_vars_secret_provider.py`**

- Использует `_ENV_PREFIX` из `secret_keys.py` (вместо жёстко заданного `"TG_EXPORTER_"`)

**Файл: `tg_exporter/secrets/env_file_secret_provider.py`**

- `.env` файл читается как есть (ключи уже с префиксом в файле)
- Провайдер ищет ключ как есть (без добавления префикса, т.к. в `.env` ключи пишутся пользователем вручную)

---

## Шаг 7. TelethonClientManager — SecretProvider вместо CredentialsManager

**Файл: `tg_exporter/telegram/telegram_client_manager.py`**

- Конструктор: `(config: AppConfig, secrets: SecretProvider)` вместо `(config, credentials)`
- `create_client()`:
  - `api_id = config.api_id_int`
  - `api_hash = config.api_hash` (из AppConfig)
  - `session_str = self._session_override or secrets.get("SESSION") or ""`
- `save_session()`: `secrets.set("SESSION", session_str)`
- Убрать все импорты `CredentialsManager`

---

## Шаг 8. ProfileManager — SecretProvider вместо CredentialsManager

**Файл: `tg_exporter/telegram/profiles/profile_manager.py`**

- Конструктор: `(secrets: SecretProvider)` вместо `(credentials)`
- `load_session()`: `self._secrets.get(f"{api_id}:session:{phone}")`
- `save_session()`: `self._secrets.set(f"{api_id}:session:{phone}", session_string)`
- `_delete_session()`: `self._secrets.delete(key)`
- `add_or_update()`: сохранять сессию через `self._secrets.set(...)`
- Убрать прямые вызовы `import keyring` / `keyring.set_password(...)` — всё через SecretProvider
- Убрать импорт `CredentialsManager`

---

## Шаг 9. ExportOrchestrator — deepgram_key из AppConfig

**Файл: `tg_exporter/services/export/export_orchestrator.py`**

- Конструктор: убрать параметр `deepgram_key`
- `_do_run()`: `create_transcriber(self._config)` — deepgram_key внутри `config.deepgram_api_key`

---

## Шаг 10. Фабрика транскриберов

**Файл: `tg_exporter/services/transcription/factory.py`**

- `create_transcriber(config: AppConfig)` — без параметра `deepgram_key`
- Читает `config.deepgram_api_key` внутри

---

## Шаг 11. CLI-команды — адаптация

**Файл: `tg_exporter_cli/commands/auth.py`**

- `auth login`:
  - `secret_provider = host.get(SecretProvider)` — остаётся (auth работает с SP напрямую)
  - `secret_provider.set("API_HASH", api_hash)` — ключ БЕЗ префикса
  - `config.api_hash = ...` — заменить на работу через `secret_provider` (config readonly)
- `auth export-session`:
  - `api_hash = secret_provider.get("API_HASH") or ""`
  - `session_str = secret_provider.get("SESSION") or ""`

**Файл: `tg_exporter_cli/commands/export.py`**

- `ExportOrchestrator(...)` — больше не передаёт `deepgram_key`

---

## Шаг 12. Тесты

**Файл: `tests/conftest.py`**

- `host_with_fake_client`: адаптировать под новый `build()` и новый `rebind_services(callback)` с сигнатурой `(container, raw_config)`

**Файл: `tests/fakes/fake_telegram_client_manager.py`**

- Убрать любые ссылки на `CredentialsManager` (если есть)

---

## Шаг 13. Cleanup

- Убрать импорт `CredentialsManager` из `cli_host.py`
- `CredentialsManager` файл не удалять (будет удалён отдельно)
- Убрать неиспользуемые импорты во всех затронутых файлах

---

## Порядок реализации

| # | Шаг | Файлы |
|---|-----|-------|
| 1 | CliHost: `_configure_cli` + `_bind_services` + новый `rebind_services` | `cli_host.py` |
| 2 | CliConfig: frozen + `from_raw` + новые поля | `cli_config.py` |
| 3 | config_mapper | `config_mapper.py` (новый) |
| 4 | AppConfig: frozen + `api_hash` | `app_config.py` |
| 5 | cli_config_repository: исключить секреты из YAML | `cli_config_repository.py` |
| 6 | Константы секретов (`secret_keys.py`) | `secret_keys.py` (новый) |
| 7 | CLI-константы (`cli_constants.py`) | `cli_constants.py` (новый), `cli_config.py` |
| 8 | Согласование префикса в `EnvVarsSecretProvider` | `env_vars_secret_provider.py` |
| 9 | TelethonClientManager: SP вместо CredentialsManager | `telegram_client_manager.py` |
| 10 | ProfileManager: SP вместо CredentialsManager | `profile_manager.py` |
| 11 | ExportOrchestrator: убрать `deepgram_key` | `export_orchestrator.py` |
| 12 | Фабрика транскриберов: упростить сигнатуру | `factory.py` |
| 13 | CLI-команды: адаптировать под readonly config | `auth.py`, `export.py` |
| 14 | Тесты: адаптировать conftest, fakes | `conftest.py`, `fake_telegram_client_manager.py` |
| 15 | Cleanup: убрать CredentialsManager из импортов | `cli_host.py` и др. |
