# Code Review: telegram-exporter

## Инструментальный прогон

| Инструмент | Результат |
|---|---|
| **Ruff** | 264 ошибки (217 автофиксимы) |
| **Pytest** | 8 failed / 181 passed (95.6%) |

### Упавшие тесты (pytest)
1. `test_full_flow_auth_and_export` — AttributeError: 'FakeTelegramClient' object has no attribute 'get_raw_telegram_client'
2. `test_secrets_source_defaults_to_keyring` — AssertionError: 'file' != 'keyring'
3. `test_message_entity_text_url` — assert 0 == 1 (links пуст)
4. `test_message_entity_text_url_label_equals_url` — IndexError: list index out of range
5. `test_message_entity_url` — IndexError: list index out of range
6. `test_deduplicate_by_url` — assert 0 == 1 (links пуст)
7. `test_from_name_and_username` — from_name = None вместо "John"
8. `test_links_extraction` — assert 0 == 1 (links пуст)

### Типовые ошибки Ruff
- ~~**UP045** — `Optional[X]` вместо `X | None`~~ ✅ исправлено (109 ошибок, `ruff check --fix --select UP045`)
- ~~**I001** — несортированные импорты~~ ✅ замьючены в `pyproject.toml`
- **B904** — `raise` без `from err` в except-блоках (~10 шт.)
- **E501** — строки длиннее 120 символов (3 шт.)
- ~~**F401** — неиспользуемые импорты~~ ✅ замьючены в `pyproject.toml`
- **UP035** — импорт типов из `typing` вместо `collections.abc` (6 шт.)
- **UP037** — кавычки в forward-reference аннотациях (5 шт.)
- **C416** — избыточное set-comprehension (1 шт.)
- **B027** — пустой метод в ABC без @abstractmethod (1 шт.)
- **W292** — нет перевода строки в конце файла (1 шт.)

---

## CRITICAL (12 проблем)

### 1. `StaticConfig(frozen=True)` с мутабельным `MarkdownSettings`
- **Файл:** `tg_exporter/hosting/static_config.py:34`
- **Описание:** `MarkdownSettings` — не-frozen `@dataclass`. Поле `markdown` в `StaticConfig` — ссылка на мутабельный объект. Любой потребитель может изменить `config.markdown.words_per_file`, нарушив контракт иммутабельности.
- **Исправление:** сделать `MarkdownSettings` frozen.

### 2. `disconnect()` без `await` — утечка TCP-соединений
- **Файл:** `tg_exporter/telegram/telethon_client_adapter.py:125,143`
- **Описание:** `load_session()` и `destroy()` — синхронные, вызывают `self._client.disconnect()` без `await`. Telethon-метод `disconnect()` — асинхронный, без `await` возвращает корутину, реального закрытия не происходит.
- **Исправление:** использовать `asyncio.run_coroutine_threadsafe(self._client.disconnect(), self._loop)`.

### 3. Сессия не удаляется из `ISecretStore` при logout
- **Файл:** `tg_exporter/telegram/auth/auth_service.py:154-165`
- **Описание:** `logout()` инвалидирует сессию на сервере и вызывает `manager.destroy()`, но **не удаляет** session string из `ISecretStore`. При следующем запуске невалидная сессия вызывает повторные ошибки.
- **Исправление:** добавить удаление сессии из secret store в `logout()`.

### 4. `get_raw_telegram_client()` отсутствует в интерфейсе — нарушение LSP
- **Файл:** `tg_exporter/telegram/telegram_client_interface.py`
- **Описание:** Метод определён только в `TelethonClientAdapter:132`. `ExportOrchestrator:104` вызывает `client.get_raw_telegram_client()` — грубое нарушение принципа подстановки Лисков. `FakeTelegramClient` не имеет этого метода → тест падает.
- **Исправление:** добавить метод в `TelegramClientInterface` или убрать вызов сырого клиента из `ExportOrchestrator`.

### 5. `FakeTelegramClient` не соответствует `TelegramClientInterface`
- **Файл:** `tests/fakes/fake_telegram_client.py:98`
- **Описание:** `iter_messages` — синхронный (должен быть `async`), первый параметр `entity` вместо `peer_id: int`, лишние параметры `reverse`, `reply_to`.
- **Исправление:** привести сигнатуру к интерфейсу.

### 6. CI/CD не запускает тесты
- **Файл:** `.github/workflows/build_release.yml`
- **Описание:** Workflow собирает бинарники, но нигде не запускает `pytest` или `ruff`. Релиз может быть собран с багами.
- **Исправление:** добавить job `test` перед сборками.

### 7. CI создаёт тег при любом результате
- **Файл:** `.github/workflows/build_release.yml:98-103`
- **Описание:** Job `release` создаёт git-тег и пушит его безусловно, даже если сборки упали.
- **Исправление:** добавить `if: success()` и проверку наличия всех артефактов.

### 8. `secrets.json` содержит реальные ключи в рабочей копии
- **Файл:** `secrets.json`
- **Описание:** Файл содержит валидные API_ID, API_HASH и SESSION. Файл не в git, но лежит в дереве исходников — бекапы IDE, копирование директории = утечка.
- **Исправление:** переместить `secrets.json` за пределы репозитория, отозвать сессию в Telegram.

### 9. `secrets.env` не в `.gitignore`
- **Файл:** `.gitignore`
- **Описание:** Команда `export-session` создаёт `secrets.env` с API_HASH, API_ID, SESSION. Файла нет в `.gitignore`. Случайный `git add .` = компрометация.
- **Исправление:** добавить `*.env` в `.gitignore`.

### 10. `auth_service.py` напрямую зависит от Telethon (нарушение архитектуры)
- **Файл:** `tg_exporter/telegram/auth/auth_service.py:12`
- **Описание:** Импортирует 12 классов из `telethon.errors`. ARCHITECTURE.md декларирует `converter.py` и `telethon_client_adapter.py` как единственные точки контакта с Telethon.
- **Исправление:** вынести маппинг ошибок в `telethon_client_adapter.py`.

### 11. Глобальный синглтон `AppLogger` (нарушение DI)
- **Файл:** `tg_exporter/utils/logger.py:101`
- **Описание:** `logger = AppLogger()` — модульный глобальный экземпляр, создаваемый при импорте. Противоречит принципу «никаких глобальных синглтонов». Race condition при `init_logger()` в параллельных тестах.
- **Исправление:** регистрировать `AppLogger` в `CliHost._bind_services()`, передавать через конструкторы.

### 12. Утечка Telethon-клиентов в CLI-командах
- **Файлы:** `tg_exporter_cli/commands/chats.py:32-38`, `tg_exporter_cli/commands/export.py:282`
- **Описание:** `create_client()` + `connect()` без `disconnect()`. В режиме `--all` каждый чат оставляет открытое соединение.
- **Исправление:** обернуть в `try/finally` с `disconnect()`.

---

## HIGH (13 проблем)

### 1. `--profile` опция не работает нигде
- **Файлы:** `tg_exporter_cli/commands/auth.py:28,83,96,132`, `tg_exporter_cli/commands/export.py:67`
- **Описание:** Задекларирована в auth и export, но **не передаётся** в сервисы. Пользователь ожидает смены аккаунта — этого не происходит.
- **Исправление:** реализовать передачу профиля в сервисы или убрать опцию.

### 2. `config set` — заглушка, изменения не сохраняются
- **Файл:** `tg_exporter_cli/commands/config_cmd.py:106-107`
- **Описание:** Команда парсит значение, но не записывает в config.json. Пользователь получает сообщение «отредактируйте вручную».
- **Исправление:** реализовать запись в config.json или скрыть команду.

### 3. `ExportTask.chat_id = 0` для username-based экспорта
- **Файл:** `tg_exporter_cli/commands/export.py:215`
- **Описание:** Когда `--chat` получает username, `chat_id` становится `0`. Может привести к коллизиям в истории экспорта.
- **Исправление:** сделать `chat_id` опциональным (`int | None`) или резолвить до создания `ExportTask`.

### 4. `auth verify` расхождение exit-кодов с docstring
- **Файл:** `tg_exporter_cli/commands/auth.py:133-143`
- **Описание:** Help обещает код 2 (нет сессии), реально возвращается 1. CI/CD скрипты, полагающиеся на код 2, будут введены в заблуждение.
- **Исправление:** привести docstring к реальному поведению или добавить различение.

### 5. DI-контейнер пересобирается при каждом вызове подкоманды
- **Файл:** `tg_exporter_cli/main.py:22-23`
- **Описание:** `cli()` создаёт новый `CliHost`, читает конфиги с диска при каждом запуске, включая `--help`. Инициализация может упасть до показа справки.
- **Исправление:** внедрить lazy-инициализацию.

### 6. Сборочные скрипты не устанавливают зависимости проекта
- **Файлы:** `scripts/build_linux.sh:15-28`, `scripts/build_mac.sh:39-53`, `scripts/build_win.ps1:18`
- **Описание:** Устанавливается только `pyinstaller`, но не `pip install .`. PyInstaller может не найти все зависимости → неполный бинарник.
- **Исправление:** добавить `pip install .` перед PyInstaller.

### 7. `build_mac.sh` не устанавливает системные зависимости
- **Файл:** `scripts/build_mac.sh:39`
- **Описание:** На macOS PyInstaller требует бинарники (upx, Xcode tools). faster-whisper требует libomp.
- **Исправление:** добавить `brew install`.

### 8. Имя файла не соответствует имени класса: `telegram_client_manager.py` → `TelethonClientManager`
- **Файл:** `tg_exporter/telegram/telegram_client_manager.py:20`
- **Описание:** Правило «один файл = один класс, имя в snake_case от имени класса» нарушено.
- **Исправление:** переименовать файл в `telethon_client_manager.py` или класс в `TelegramClientManager`.

### 9. Имя файла не соответствует имени класса: `logger.py` → `AppLogger`
- **Файл:** `tg_exporter/utils/logger.py:46`
- **Описание:** Нарушение правила snake_case от имени класса.
- **Исправление:** переименовать файл в `app_logger.py`.

### 10. Несогласованность ABC-интерфейсов
- **Файлы:** `secret_store.py`, `settings_store.py`, `telegram_client_interface.py`, `telegram_client_manager_interface.py`, `transcription/base.py`, `exporters/base_exporter.py`
- **Описание:** Три стиля: `I`-префикс (`ISecretStore`), `Base`-префикс (`BaseTranscriber`), `Interface`-суффикс (`TelegramClientInterface`).
- **Исправление:** выбрать один стиль, рекомендован `I`-префикс.

### 11. `keyring_secret_store.py` использует стандартный `logging` вместо `AppLogger`
- **Файл:** `tg_exporter/secrets/keyring_secret_store.py:4,9,22,30,37`
- **Описание:** Использует `logging.getLogger(__name__)` без `AppLogger.redact()`. При ошибках keyring traceback выводится без редактирования секретов.
- **Исправление:** заменить на проектный `AppLogger`.

### 12. Секреты в `StaticConfig` (DI-singleton)
- **Файл:** `tg_exporter/hosting/configuration_provider.py:104-105`, `tg_exporter_cli/hosting/cli_host.py:49-53`
- **Описание:** `api_hash` и `deepgram_api_key` мапятся в поля `StaticConfig`, доступного всем компонентам через DI. При случайном логировании конфига секреты утекут.
- **Исправление:** убрать секреты из `StaticConfig`, получать через `ISecretStore`.

### 13. `_extract_links` использует `type().__name__` вместо `isinstance()`
- **Файл:** `tg_exporter/telegram/converter.py:172-194`
- **Описание:** Сравнение `cls_name == "MessageEntityTextUrl"` сломается при рефакторинге Telethon.
- **Исправление:** использовать `isinstance(ent, MessageEntityTextUrl)`.

---

## MEDIUM (18 проблем)

1. **`_build_forwarded_from` некорректно с `Peer`** — `tg_exporter/telegram/converter.py:117-118` — `from_id` это Peer-объект, `str()` на нём даёт нечитаемую строку
2. **Premium-реакции (кастомные эмодзи) теряются** — `tg_exporter/telegram/converter.py:131` — `ReactionItem` не имеет поля `document_id`
3. **`sign_in` без `phone_code_hash`** — `tg_exporter/telegram/telethon_client_adapter.py:81` — хеш не передаётся явно, зависит от внутреннего состояния сессии
4. **Конвертер не обрабатывает 7+ типов медиа** — `tg_exporter/telegram/converter.py:199-215` — contact, geo, dice, game, web_page, invoice теряются
5. **Сервисные сообщения теряют данные** — `tg_exporter/telegram/converter.py:27,57-58` — кроме названия топика, всё теряется
6. **Нет обработки `FloodWaitError` в экспорте** — `tg_exporter/telegram/telethon_client_adapter.py:91-101` — длительный экспорт может прерваться
7. **Не-frozen dataclasses** — `MarkdownSettings`, `AuthResult`, `AudioPrepResult`, `MediaDirs`, `Profile`, `AnalyticsResult`, `AuthorStats`
8. **Несколько классов в одном файле** — `configuration_provider.py`, `state_model.py`, `export_format.py`, `poll_data.py`, `markdown_settings.py`, `telegram_client_manager.py`, `cancellation.py`
9. **Дублирование логики event loop** — 4 места: `export_orchestrator.py`, `async_runner.py`, `telethon_client_adapter.py`, `media_downloader.py`
10. **Дублирование `_run_download` в media_downloader.py** — строки 79-84 и 238-245
11. **`MediaDirs.for_media_type()` — zombie code** — `tg_exporter/services/media_downloader/media_dirs.py:34-43`
12. **Отсутствуют тесты на транскрипцию и медиа-загрузку** — `transcription/`, `media_downloader/` не покрыты
13. **Зависимость тестов от `time.sleep()`** — `tests/test_models.py:181,219`, `tests/test_services.py:277` — флапает на перегруженном CI
14. **Дублирование тестов ExportHistory** — `tests/test_services.py` и `tests/unit/test_export_history.py`
15. **`_interface_map` / `register_interface` — мёртвый код** — `tg_exporter_cli/hosting/container.py:15,25-27`
16. **`asyncio.get_event_loop()` — deprecated** — `tg_exporter_cli/utils/async_runner.py:12`
17. **`requirements.txt` дублирует `pyproject.toml`** — источники рассинхронизации зависимостей
18. **Версия `1.0.0` захардкожена** — не синхронизируется с CI-инкрементом

---

## LOW (выборочно)

- Неиспользуемые импорты: `get_peer_id` в converter.py, `TYPE_CHECKING` в converter.py, `ConfigurationResult` в auth.py, `logger` в profile_manager.py
- Неиспользуемые константы: `DEFAULT_ENV_FILENAME` в cli_constants.py
- Неиспользуемый код: `CancellationToken.reset()`, `CancellationToken.wait_for_cancel()`, `retry_async`, `TelethonClientAdapter.load_session`, `base_exporter.sanitize_filename` (re-export)
- Windows-специфичные: нет проверки MAX_PATH при формировании путей экспорта; `_safe_name()` regex удаляет легальные символы; `\r`-прогресс без flush
- `bump_version.sh` — `sed -i` не переносим между Linux/macOS
- `build_win.ps1` — `$MyInvocation.MyCommand.Path` устарел, использовать `$PSScriptRoot`
- `keyring>=24.0,<26.0` — узкая верхняя граница
- Нестандартный `raise SystemExit(1)` вместо `sys.exit(1)` / `ctx.exit(1)`
- `WhisperTranscriber._download_model_with_progress` — мутабельный `shared` dict без блокировки
- `ExportTask.deepgram_api_key` — zombie field, нигде не читается
- `JsonSecretStore._write` — временный `.tmp` файл не чистится при ошибке `os.replace()`

---

## Вердикт

### ❌ Код НЕ готов к публикации

**Блокирующие проблемы (12 CRITICAL):**
- Архитектурные нарушения (Telethon в auth_service, глобальный синглтон logger)
- Утечки ресурсов (TCP без disconnect, клиенты без закрытия)
- Нарушение абстракций (get_raw_telegram_client в обход интерфейса, FakeTelegramClient не соответствует интерфейсу)
- Падающие тесты (FakeTelegramClient не реализует get_raw_telegram_client)
- CI не тестирует код перед релизом
- Реальные секреты в рабочей копии (secrets.json)
- `.gitignore` пропускает `*.env`

**Рекомендуемый порядок исправления:**
1. CRITICAL (архитектура, утечки, секреты, CI)
2. HIGH (нерабочие фичи, несогласованность имён, безопасность)
3. `ruff check --fix` + `ruff format` (автофикс 217 ошибок)
4. MEDIUM (техдолг)
