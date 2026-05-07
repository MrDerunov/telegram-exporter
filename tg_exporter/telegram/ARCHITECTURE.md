# Core Layer — аутентификация и управление клиентом

## Назначение

Core-слой отвечает за подключение к Telegram API, аутентификацию пользователя, хранение секретов и управление несколькими аккаунтами. Все классы этого слоя — чистые сервисы без UI-зависимостей.

## Компоненты

### CredentialsManager (`telegram/credentials_manager.py`)

Единственное место, где хранятся секреты приложения.

**Контракт:**
- `api_hash`, session string, Deepgram API key → **только в системном Keyring**
- Никакого fallback к plaintext
- Если Keyring недоступен → `KeyringUnavailableError`
- `api_id` — публичный идентификатор, хранится отдельно в `config.json`

**Структура ключей в Keyring (service=`tg_exporter`):**

| Ключ               | Значение         |
|---------------------|------------------|
| `{api_id}:api_hash` | api_hash         |
| `{api_id}:session`  | session string   |
| `deepgram_api_key`  | Deepgram API key |

**Миграция:** метод `migrate_from_plaintext()` переносит секреты из старого конфига в Keyring. Plaintext-файл очищается только при успешной миграции.

### TelegramClientManager (`telegram/telegram_client_manager.py`)

Управляет жизненным циклом `Telethon.TelegramClient`.

**Обязанности:**
- Создание клиента из credentials (api_id из конфига, api_hash/session из Keyring)
- Один asyncio event loop на весь поток
- Ленивое создание: клиент создаётся при первом `get_client()`
- Переключение сессий через `use_session()` (для мульти-аккаунтов)
- Сохранение сессии через `save_session()`

**Thread-safety:** внутренний `threading.Lock` защищает создание/уничтожение клиента.

**Ошибка:** `ClientNotConfiguredError` — если `api_id` или `api_hash` не заданы.

### AuthService (`telegram/auth/auth_service.py`)

Оркестратор процесса аутентификации в Telegram. Полностью отделён от UI.

**Публичный API:**
```
send_code(phone)    → AuthResult(code_sent | success | error)
verify_code(code)   → AuthResult(success | password_required | error)
verify_password(pwd)→ AuthResult(success | error)
check_session()     → AuthResult(success | error)
logout()
```

**Модель AuthStep** (`telegram/auth/auth_step.py`): enum — `CODE_SENT`, `PASSWORD_REQUIRED`, `SUCCESS`, `ERROR`.

**Модель AuthResult** (`telegram/auth/auth_result.py`): dataclass с полями `step` и `error`. Ошибки преобразуются в читаемый русский текст через `_friendly()`.

### ProfileManager (`telegram/profiles/profile_manager.py`)

CRUD над несколькими Telegram-аккаунтами.

**Модель Profile** (`telegram/profiles/profile.py`): dataclass с полями `phone`, `display_name`, `api_id`. В этом же файле вспомогательные функции `_session_key()` и `_normalize_phone()`.

**API:**
```
list() → list[Profile]
active() → Profile | None
add_or_update(phone, api_id, session_string) → Profile
set_active(phone) → Profile | None
remove(phone) → bool
load_session(profile) → str | None
```

**Хранение:**
- Метаданные (phone, display_name, api_id) → `~/.tg_exporter/profiles.json`
- Сессии → Keyring под ключом `{api_id}:session:{phone}`

**Thread-safety:** внутренний `threading.Lock` на чтение/запись profiles.json.

### Converter (`telegram/converter.py`)

Единственный модуль, который знает про Telethon.

**Функция `message_to_export(message) → ExportMessage`:**
- Извлекает все данные из Telethon `Message`
- Преобразует в иммутабельный `ExportMessage` (чистые Python-типы)
- Извлекает: текст, автора, реакции, опросы, ссылки, топики, forwarded_from
- Определяет `MediaType` без скачивания (по наличию атрибутов: photo, video, voice, etc.)

Ни один другой сервис не импортирует Telethon напрямую.

## Связи с другими слоями

```
UI (App)
  │
  ├──→ CredentialsManager ──→ Keyring
  ├──→ TelegramClientManager ──→ Telethon.Client
  ├──→ AuthService ──→ TelegramClientManager
  ├──→ ProfileManager ──→ CredentialsManager
  │
  └──→ ExportOrchestrator ──→ TelegramClientManager + Converter
```

## Поток аутентификации

```
1. Пользователь вводит api_id + api_hash
2. CredentialsManager.save_api_hash() → Keyring
3. AuthService.send_code(phone) → Telethon.send_code_request()
4. AuthService.verify_code(code) → Telethon.sign_in()
5. При 2FA: AuthService.verify_password(pwd)
6. После успеха: client.save_session() + ProfileManager.add_or_update()
```
