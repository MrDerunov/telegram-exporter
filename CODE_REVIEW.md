# Code Review: telegram-exporter

## Инструментальный прогон

| Инструмент | Результат |
|---|---|
| **Ruff** | 23 ошибки |
| **Pytest** | 0 failed / 279 passed (100%) |

### Ошибки Ruff (23)

| Код | Кол-во | Описание |
|-----|--------|----------|
| UP017 | 6 | `datetime.UTC` alias вместо `timezone.utc` |
| C408 | 6 | `dict()` вместо литерала `{}` |
| E501 | 3 | Строка длиннее 120 символов |
| E741 | 3 | Неоднозначное имя переменной `l` |
| UP047 | 2 | Generic-функции должны использовать type parameters |
| F811 | 1 | Переопределение `error` в `AuthResult` |
| UP041 | 1 | Заменить алиасы ошибок на `TimeoutError` |
| B017 | 1 | `pytest.raises(Exception)` — слепой assert |

---

## HIGH (8 проблем)

### 1. DI-контейнер пересобирается при каждом вызове подкоманды
- **Файл:** `tg_exporter_cli/main.py:19-22`
- **Описание:** `CliHost().build()` выполняется при каждом запуске, включая `--help`.

### 2. Сборочные скрипты не устанавливают системные зависимости
- **Файл:** `scripts/build_mac.sh`
- **Описание:** Отсутствуют `brew install` для зависимостей PyInstaller/faster-whisper.

### 3. Имя файла не соответствует имени класса: `telegram_client_manager.py` → `TelethonClientManager`
- **Файл:** `tg_exporter/services/telegram/telegram_client_manager.py:19`
- **Описание:** Правило «один файл = один класс, имя в snake_case от имени класса» нарушено.

### 4. Имя файла не соответствует имени класса: `logger.py` → `AppLogger`
- **Файл:** `tg_exporter/utils/logger.py:47`
- **Описание:** Нарушение правила snake_case от имени класса.

### 5. Несогласованность ABC-интерфейсов
- **Файлы:** `secret_store.py` (`ISecretStore`), `settings_store.py` (`ISettingsStore`), `telegram_client_interface.py` (`TelegramClientInterface`), `telegram_client_manager_interface.py` (`ITelegramClientManager`), `transcription/base.py` (`BaseTranscriber`), `exporters/base_exporter.py` (`BaseExporter`)
- **Описание:** Три стиля: `I`-префикс, `Base`-префикс, `Interface`-суффикс.

### 6. `keyring_secret_store.py` использует стандартный `logging` вместо `AppLogger`
- **Файл:** `tg_exporter/settings/secrets/keyring_secret_store.py:4,8,21,29,36`
- **Описание:** `logging.getLogger(__name__)` без `AppLogger.redact()`. Секреты могут утечь в лог.

### 7. Секреты в `StaticConfig` (DI-singleton)
- **Файлы:** `tg_exporter/settings/configs/static_config.py:16-17`, `tg_exporter_cli/hosting/cli_host.py:56-59`
- **Описание:** `api_hash` и `deepgram_api_key` доступны всем компонентам через DI. При логировании — утечка.

### 8. `_extract_links` использует `type().__name__` вместо `isinstance()`
- **Файл:** `tg_exporter/services/telegram/converter.py:171-184`
- **Описание:** Сравнение `cls_name == "MessageEntityTextUrl"` сломается при рефакторинге Telethon.

---

## MEDIUM (15 проблем)

1. **`_build_forwarded_from` некорректно с `Peer`** — `tg_exporter/services/telegram/converter.py:117-118` — `from_id` это Peer-объект, `str()` даёт нечитаемую строку
2. **Premium-реакции (кастомные эмодзи) теряются** — `tg_exporter/services/telegram/converter.py:122-131` — нет проверки `reaction.document_id`
3. **`sign_in` без `phone_code_hash`** — `tg_exporter/services/telegram/telethon_client_adapter.py:81` — хеш не передаётся явно
4. **Конвертер не обрабатывает 7+ типов медиа** — `tg_exporter/services/telegram/converter.py:197-214` — contact, geo, dice, game, web_page, invoice теряются
5. **Сервисные сообщения теряют данные** — `tg_exporter/services/telegram/converter.py:25,55-56` — кроме названия топика, всё теряется
6. **Нет обработки `FloodWaitError` в экспорте** — экспорт может прерваться при длительной выгрузке
7. **Не-frozen dataclasses** — `AuthResult`, `AudioPrepResult`, `MediaDirs`, `AnalyticsResult`, `AuthorStats`
8. **Несколько классов в одном файле** — `configuration_provider.py`, `state_model.py`, `export_format.py`, `poll_data.py`, `telegram_client_manager.py`, `cancellation.py`
9. **Дублирование логики event loop** — `async_runner.py`, `telethon_client_adapter.py`, `media_downloader.py`
10. **`MediaDirs.for_media_type()` — zombie code** — `tg_exporter/services/media_downloader/media_dirs.py:33-42`
11. **Отсутствуют тесты на транскрипцию и медиа-загрузку** — `transcription/`, `media_downloader/` не покрыты
12. **Зависимость тестов от `time.sleep()`** — `tests/unit/test_export_task.py:39,71`, `tests/integration/commands/test_export_deduplicate.py:69,123`, `tests/integration/commands/test_export_resume.py:84`
13. **`_interface_map` / `register_interface` — мёртвый код** — `tg_exporter_cli/hosting/container.py:16,26-27`
14. **`asyncio.get_event_loop()` — deprecated** — `tg_exporter_cli/utils/async_runner.py:13`, `tg_exporter/services/telegram/telethon_client_adapter.py:38`
15. **`requirements.txt` дублирует `pyproject.toml`** — источники рассинхронизации зависимостей

---

## LOW (выборочно)

- `CancellationToken.wait_for_cancel()` — не используется в production-коде
- `retry_async` в `tg_exporter/utils/retry.py` — не используется
- `TelethonClientAdapter.load_session` — не используется
- `base_exporter.sanitize_filename` — re-export без потребителей
- `DEFAULT_ENV_FILENAME` в `cli_constants.py` — не используется
- `bump_version.sh` — `sed -i` не переносим между Linux/macOS
- `build_win.ps1` — `$MyInvocation.MyCommand.Path` устарел
- `keyring>=24.0,<26.0` — узкая верхняя граница
- Нестандартный `raise SystemExit(1)` вместо `sys.exit(1)` / `ctx.exit(1)`
- `WhisperTranscriber._download_model_with_progress` — мутабельный `shared` dict без блокировки
- `ExportTask.deepgram_api_key` — zombie field, нигде не читается
- `JsonSecretStore._write` — временный `.tmp` файл не чистится при ошибке `os.replace()`
- Windows: нет проверки MAX_PATH; `_safe_name()` regex удаляет легальные символы; `\r`-прогресс без flush
