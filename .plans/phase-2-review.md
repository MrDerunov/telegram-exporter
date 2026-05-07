# Ревью Фазы 2: Команды и тесты (MVP)

## Общая оценка: ⚠️

Код в целом соответствует плану, но есть несколько критичных багов в тестах (неправильные моки и тестовые объекты), которые мешают их прохождению. Команды реализованы корректно за исключением одного отклонения от плана в `auth verify` (только 2 exit code вместо 3).

## Замечания

### Критичные (❌)

**1. `auth verify` — только 2 exit code вместо заявленных 3**
- План: exit codes 0 (валидна), 1 (невалидна), 2 (нет сессии)
- Факт: только 0 и 1. `AuthStep` enum не имеет состояния "NO_SESSION", поэтому различие между "нет сессии" и "невалидна" не реализовано
- Файл: `tg_exporter_cli/commands/auth.py:98-107`

**2. `test_converter.py` — `_extract_links` тесты падают из-за неправильных class name entity**
- `_extract_links()` проверяет `type(ent).__name__` на `"MessageEntityTextUrl"` и `"MessageEntityUrl"`
- Тесты создают объекты с именами классов `"TE"` и `"UE"` — не совпадает → возвращается пустой список
- Файлы: `tg_exporter/telegram/converter.py:186-208`, `tests/unit/test_converter.py`

**3. `test_converter.py` — `test_from_name_and_username` падает**
- Тест создаёт fake-sender через `type("FakeSender", ...)()`, но реальный `telethon.utils.get_display_name()` не распознаёт этот объект и возвращает пустую строку → `from_name = None`
- Файлы: `tests/unit/test_converter.py:272-276`, `tg_exporter/telegram/converter.py:33-36`

**4. `test_secrets.py` — все тесты KeyringSecretProvider падают (×7)**
- Мок `patch("tg_exporter.secrets.keyring_secret_provider.keyring")` не работает: `keyring` импортируется локально внутри методов (`import keyring`), а не на уровне модуля
- Нужно либо мокать на уровне вызова (например `patch("keyring.get_password")`), либо переписать импорты в провайдере на модульные
- Файлы: `tg_exporter/secrets/keyring_secret_provider.py`, `tests/unit/test_secrets.py`

**5. `test_secrets.py` — `test_dotenv_not_installed_fallback` падает**
- Аналогичная проблема: `dotenv_values` импортируется локально внутри `_load()`, не на уровне модуля
- Path `"tg_exporter.secrets.env_file_secret_provider.dotenv_values"` не существует
- Файлы: `tg_exporter/secrets/env_file_secret_provider.py`, `tests/unit/test_secrets.py`

**6. `test_secrets.py` — `test_chain_order_respected` падает**
- Используются два `EnvVarsSecretProvider` с ожиданием изоляции, но они оба пишут в одни и те же переменные окружения OS
- `ev2.set("ORDER_KEY", "second")` перезаписывает значение, установленное `ev1.set("ORDER_KEY", "first")`
- Нужно использовать провайдеры с изолированным хранилищем (например `EnvFileSecretProvider` с разными файлами)
- Файл: `tests/unit/test_secrets.py:217-224`

### Важные (⚠️)

**7. `export-session` полагается на `hasattr(client, "save_session")`**
- `TelegramClientInterface` не объявляет метод `save_session()` — он есть только у `TelethonClientAdapter`
- При использовании других реализаций `export-session` молча вернёт пустую строку, что приведёт к невалидному `secrets.env`
- Рекомендация: либо добавить метод в ABC, либо выбрасывать явную ошибку если `hasattr` возвращает False
- Файл: `tg_exporter_cli/commands/auth.py:84-85`

**8. `export.py` вручную создаёт event loop вместо `run_async()`**
- Создаёт `asyncio.new_event_loop()` и вызывает `loop.run_until_complete()` для разрешения диалога
- Хелпер `run_async()` специально создан для этого — но не используется
- Файл: `tg_exporter_cli/commands/export.py:79-94`

**9. `export.py` вручную разрешает диалоги, обходя оркестратор**
- Вызывает `create_client().connect().get_dialogs()` напрямую, вместо того чтобы позволить оркестратору сделать это
- Создаёт fallback-диалог через `_fallback_dialog()` если чат не найден
- Это нарушает инкапсуляцию — оркестратор должен сам управлять поиском диалогов
- Файл: `tg_exporter_cli/commands/export.py:79-96`

**10. `auth login` не сохраняет конфиг после установки `api_id`**
- `container.config.api_id = api_id` меняет значение в памяти, но `container.config.save()` не вызывается
- При следующем запуске контейнера api_id из опции будет потерян
- Файл: `tg_exporter_cli/commands/auth.py:26-27`

### Мелкие (💡)

**11. `version.py` хардкодит "1.0.0"**
- Версию лучше читать из `pyproject.toml` или `_version.py`
- Файл: `tg_exporter_cli/commands/version.py`

**12. `doctor.py` хардкодит путь к конфигу**
- `config_path = DEFAULT_CONFIG_DIR / "cli_config.yaml"` — лучше использовать `Container` для определения фактического пути
- Файл: `tg_exporter_cli/commands/doctor.py:29`

**13. Дублирование тестов экспортеров**
- `tests/test_exporters.py` (Phase 1, unittest, 275 строк) и `tests/unit/test_exporters.py` (Phase 2, pytest, 179 строк)
- Оба тестируют `JsonExporter` и `MarkdownExporter`
- Рекомендация: удалить Phase 1-версию или консолидировать в один файл

**14. `auth login` сообщение отличается от плана**
- План: «✅ Авторизован как @username»
- Факт: «✅ Авторизован успешно» (без username)
- Файл: `tg_exporter_cli/commands/auth.py:57`

**15. `main.py` — команды-заглушки chats/profile/config оставлены как и требуется**
- ✅ Заглушки `chats list`, `profile list`, `config show` присутствуют с `[TODO]`

## Соответствие плану (checklist)

### Задача A: auth-команды
- [x] `auth login` — 5 опций, интерактивный вход
- [x] `auth status` — проверка статуса
- [x] `auth logout` — выход
- [x] `auth export-session` — экспорт с 0o600 ✅, предупреждение ✅
- [⚠️] `auth verify` — exit codes: только 0/1 вместо 0/1/2
- [x] Использует `run_async()` для async AuthService ✅

### Задача B: export-команда
- [x] `export run` — опции `--chat`, `--output`, `--format`, `--last`
- [x] Создаёт `ExportTask` с правильными параметрами (включая `message_limit`)
- [⚠️] Использует `container.orchestrator` ✅, но вручную резолвит диалоги
- [x] Выводит прогресс через callback

### Задача C: version и doctor
- [x] `version` показывает версию и платформу ✅
- [x] `doctor` проверяет Python, конфиг, keyring, сессию, ffmpeg, место ✅

### Задача D: тесты
- [x] Unit: converter, export_history, secrets, exporters — все 4 ✅
- [x] Integration: auth_command, export_command, end_to_end — все 3 ✅
- [❌] Тесты используют реальные сигнатуры из кода — в целом да, но есть баги с моками и fake-объектами
- [x] conftest с нужными фикстурами ✅

### Задача E: main.py
- [x] Auth, export, version, doctor импортируются из commands ✅
- [x] Заглушки chats/profile/config оставлены ✅
- [x] Нет дублирования команд ✅

### AsyncRunner
- [x] Корректно запускает async из sync Click ✅
- [x] Обрабатывает closed loop ✅

## Итог

Кодовая база в хорошем состоянии. Основные проблемы — в тестах: неправильные моки (keyring, dotenv — локальные импорты), неправильные fake-объекты для `_extract_links` (class name) и `get_display_name` (несовместимый с Telethon объект), и изоляция `EnvVarsSecretProvider` в chain-тесте.

**Рекомендации перед merge:**
1. Починить тесты `test_converter.py` (class names + fake sender)
2. Починить тесты `test_secrets.py` (моки + chain изоляция)
3. Решить про `auth verify` — либо добавить exit code 2, либо обновить план
4. Рассмотреть унификацию `export.py` с `run_async()` и резолвингом через оркестратор
