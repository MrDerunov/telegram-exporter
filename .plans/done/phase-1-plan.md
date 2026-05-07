# План реализации Фазы 1: Абстракция клиента и базовая инфраструктура

> Ветка: `phase/1-client-abstraction`
> Исходный план: `cli-app-plan.md` §14, «Фаза 1»

## Цель

Создать фундамент CLI-приложения: абстракцию Telegram-клиента, систему секретов и DI-контейнер. Не трогать UI-слой и десктопный код — только добавить новые модули и адаптировать существующие.

## Анализ текущей кодовой базы

### Что уже есть
- `tg_exporter/telegram/telegram_client_manager.py` — `TelegramClientManager` (жизненный цикл Telethon клиента)
- `tg_exporter/telegram/credentials_manager.py` — `CredentialsManager` (секреты только через Keyring)
- `tg_exporter/telegram/auth/auth_service.py` — `AuthService` (завязан на `TelegramClientManager`)
- `tg_exporter/services/export/export_orchestrator.py` — `ExportOrchestrator` (завязан на `TelegramClientManager`)
- `tg_exporter/telegram/profiles/profile_manager.py` — `ProfileManager`
- `tg_exporter/hosting/app_config.py` — `AppConfig`
- `tg_exporter/utils/cancellation.py` — `CancellationToken`

### Что НЕ трогаем
- `tg_exporter/ui/` — будет удалено в Фазе 4
- `tg_exporter/utils/worker.py` — будет удалено в Фазе 4
- `main.py` (корневой) — будет удалён в Фазе 4
- `tg_exporter/telegram/profiles/` — переиспользуем как есть

## Задачи (4 подзадачи для субагентов)

### Задача A: TelegramClientInterface + ITelegramClientManager + TelethonClientAdapter
**Файлы:**
- `tg_exporter/telegram/telegram_client_interface.py` — ABC с async-методами
- `tg_exporter/telegram/telegram_client_manager_interface.py` — ABC фабрики `ITelegramClientManager`
- `tg_exporter/telegram/telegram_client_manager.py` — `TelethonClientManager` (фабрика)
- `tg_exporter/telegram/telethon_client_adapter.py` — работает с `telethon.TelegramClient` напрямую

**Что делает:**
1. Создать `TelegramClientInterface(ABC)` с методами (async, из плана §3):
   - `connect()`, `disconnect()`
   - `is_authorized() -> bool`
   - `send_code_request(phone)`, `sign_in(phone, code)`, `sign_in_password(password)`
   - `get_dialogs(limit) -> list[Dialog]`
   - `iter_messages(peer_id, min_id, offset_date, limit) -> AsyncIterator[Message]`
   - `download_media(message, path) -> Path | None`
   - `destroy()` (уничтожение клиента)
2. Создать `ITelegramClientManager(ABC)` — фабрика с методами `create_client()`, `save_session()`, `destroy()`
3. Создать `TelethonClientManager` — реализует `ITelegramClientManager`, создаёт `TelethonClientAdapter` с нужной сессией
4. Создать `TelethonClientAdapter` — реализует `TelegramClientInterface`, работает с `telethon.TelegramClient` напрямую (без прослойки)
5. Экспортировать классы через `tg_exporter/telegram/__init__.py`

### Задача B: SecretProvider + реализации
**Файлы:**
- `tg_exporter/secrets/__init__.py`
- `tg_exporter/secrets/secret_provider.py` — `SecretProvider(ABC)` с `writable: bool = False`
- `tg_exporter/secrets/env_vars_secret_provider.py` — `EnvVarsSecretProvider` (os.environ, writable=True)
- `tg_exporter/secrets/env_file_secret_provider.py` — `EnvFileSecretProvider` (.env, writable=False)
- `tg_exporter/secrets/chain_secret_provider.py` — `ChainSecretProvider`
- `tg_exporter/secrets/keyring_secret_provider.py` — `KeyringSecretProvider` (writable=True, не используется по умолчанию)

**Что делает:**
1. `SecretProvider(ABC)` — три метода: `get(key)`, `set(key, value)`, `delete(key)` + поле `writable`
2. `EnvVarsSecretProvider` — читает из `os.environ` (writable=True, set() пишет в os.environ)
3. `EnvFileSecretProvider` — читает из `.env` через `python-dotenv` (writable=False, только чтение)
4. `KeyringSecretProvider` — обёртка над keyring (writable=True)
5. `ChainSecretProvider` — при get() пробует провайдеры по порядку, при set() пишет только в writable
6. Формат ключей: `TG_EXPORTER_API_HASH`, `TG_EXPORTER_SESSION`, `TG_EXPORTER_DEEPGRAM_KEY`

### Задача C: Container + main.py + зависимости
**Файлы:**
- `tg_exporter_cli/__init__.py`
- `tg_exporter_cli/container.py` — `Container`
- `tg_exporter_cli/main.py` — Click group skeleton
- `tg_exporter_cli/cli_config.py` — `CliConfig` (YAML)

**Что делает:**
1. `Container.__init__` собирает зависимости:
   ```
   SecretProvider → CliConfig → AppConfig → CredentialsManager
   → TelethonClientManager (ITelegramClientManager) → AuthService + ProfileManager + ExportOrchestrator
   ```
2. `main.py` — Click группа `tg-exporter` с заглушками команд:
   - `auth login/status/logout/export-session/verify`
   - `export`
   - `chats`
   - `profile`
   - `config`
   - `version`
   - `doctor`
3. Установка зависимостей: `click`, `pyyaml`, `python-dotenv`
4. `CliConfig` — минимальная модель (version, api_id, default_profile)

### Задача D: FakeTelegramClient + FakeTelegramClientManager + factories
**Файлы:**
- `tests/__init__.py`
- `tests/fakes/__init__.py`
- `tests/fakes/fake_telegram_client.py` — `FakeTelegramClient`
- `tests/fakes/fake_telegram_client_manager.py` — `FakeTelegramClientManager`
- `tests/fakes/factories.py` — фабрики тестовых данных
- `tests/conftest.py` — фикстуры (контейнер с фейковым менеджером)

**Что делает:**
1. `FakeTelegramClient(TelegramClientInterface)` — реализует все методы ABC
   - `_dialogs: list[Dialog]`, `_messages: dict[int, list[Message]]`
   - `add_dialog()`, `add_messages()`, `set_authorized()`
   - Все методы синхронные (возвращают готовые данные, не async)
2. `FakeTelegramClientManager(ITelegramClientManager)` — фейковая фабрика, создаёт `FakeTelegramClient`
3. `factories.py` — функции для генерации тестовых `ExportMessage`, `Dialog`, `ExportTask`
4. `conftest.py` — минимум: фикстуры `fake_client`, `fake_manager`, `container_with_fake_client`

## Порядок выполнения

1. ✅ Создать ветку `phase/1-client-abstraction`
2. ✅ Запустить задачи A, B, C, D параллельно (4 субагента)
3. ✅ После завершения — ревью, исправления
4. ⬜ Merge ветки в main
5. ⬜ Перенести план в `.plans/done/phase-1-plan.md`

## Критерии приёмки

- [x] `TelegramClientInterface` ABC с async-методами (без `save_session`/`load_session`/`get_client`)
- [x] `ITelegramClientManager` ABC фабрики с `create_client()`, `save_session()`, `destroy()`
- [x] `TelethonClientAdapter` реализует `TelegramClientInterface`, работает с `telethon.TelegramClient` напрямую
- [x] `TelethonClientManager` реализует `ITelegramClientManager`, создаёт `TelethonClientAdapter`
- [x] `AuthService` принимает `ITelegramClientManager`, а не raw клиент
- [x] `ExportOrchestrator` принимает `ITelegramClientManager`, а не raw клиент
- [x] Все 4 SecretProvider'а реализованы с флагом `writable`
- [x] `ChainSecretProvider` пишет только в writable
- [x] `Container` собирает все зависимости, принимает `telegram_manager` для подмены
- [x] `main.py` — Click группа с заглушками всех команд
- [x] `FakeTelegramClient` реализует `TelegramClientInterface`
- [x] `FakeTelegramClientManager` реализует `ITelegramClientManager`
- [x] Тесты проходят (unit-тесты на SecretProvider и FakeTelegramClient)
- [x] Существующий код (UI, worker) не сломан
