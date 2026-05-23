# Core Layer — аутентификация, клиент

Отвечает за подключение к Telegram API, аутентификацию, хранение секретов.

## Компоненты

### Хранение секретов: ISecretStore
Абстракция над хранилищем секретов (api_hash, session, ключи API).
- **KeyringSecretStore** — системный keyring (по умолчанию).
- **JsonSecretStore** — `secrets.json` (для CI/CD).
- Дополнительно: `TG_EXPORTER_*` и `.env` подхватываются `ConfigurationProvider`.

Ключи определены в `secret_keys.py`: `API_HASH`, `API_ID`, `SESSION`, `DEEPGRAM_API_KEY`.

`api_id` — публичный, хранится в `config.json`. `api_hash` — секретный, только через ISecretStore.

### Хранение состояния: ISettingsStore → StateModel
Чаты — в `state.json`. Модель: `StateModel` (frozen, содержит `ChatEntry`).

### ITelegramClientManager → TelethonClientManager
Управляет жизненным циклом `Telethon.TelegramClient`. Ленивое создание.
Thread-safe через `threading.Lock`.

### AuthService
Оркестратор аутентификации. Полностью отделён от UI.
- `send_code(phone)` / `verify_code(code)` / `verify_password(pwd)` → `AuthResult`
- `check_session()` — проверка валидности сессии.
- Модели: `AuthStep` (enum), `AuthResult` (dataclass).

### Converter
Единственный модуль, знающий про Telethon. `message_to_export()` преобразует Telethon `Message` в иммутабельный `ExportMessage` (чистые Python-типы). Извлекает: текст, автора, реакции, опросы, ссылки, медиа-тип, топики, пересылки.

## Связи

```
CliHost
  ├── StaticConfig (config.json)
  ├── ISecretStore (Keyring / secrets.json)
  └── ISettingsStore (state.json)
        │
   AuthService ── ITelegramClientManager
   ITelegramClientManager ── Telethon.Client
   Converter ── Telethon.Message → ExportMessage
```

## Поток аутентификации

1. api_id + api_hash → api_hash в ISecretStore
2. `send_code(phone)` → код в Telegram
3. `verify_code(code)` → вход
4. 2FA: `verify_password(pwd)`
5. Сохранение сессии в ISecretStore (ключ SESSION)
