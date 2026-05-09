# План реализации: Фаза 3 + Фаза 4

## Общая стратегия

Фазы 3 и 4 реализуются последовательно, с промежуточными коммитами после каждого логического блока. Порядок: сначала расширение экспорта (Фаза 3), затем конфигурация/профили/удаление десктопа (Фаза 4).

---

## Фаза 3: Полноценный экспорт и чаты

### 3.1. Расширение CLI-опций export (→ `tg_exporter_cli/commands/export.py`)

Добавить недостающие флаги команды `export run`:

| Флаг | Поле ExportTask | Статус |
|------|----------------|--------|
| `--date-from DATE` | `date_from` | **добавить** |
| `--date-to DATE` | `date_to` | **добавить** |
| `--days INTEGER` | вычисляется в `date_from` | **добавить** |
| `--topic-id INTEGER` | `topic_id` | **добавить** |
| `--download-media` | `download_media=True` | **добавить** |
| `--transcribe` | `transcribe=True` | **добавить** |
| `--transcriber [local\|deepgram]` | `transcriber` | **добавить** |
| `--analytics` | `analytics=True` | **добавить** |
| `--words-per-file INTEGER` | в настройках MarkdownSettings | **добавить** |
| `--profile TEXT` | выбор аккаунта | **добавить** |
| `--resume` | `incremental=True` | **добавить** |
| `--message-types [text\|media\|pinned\|all]` | `message_types` | **добавить** |

### 3.2. Валидация конфликтующих флагов (→ `tg_exporter_cli/commands/export.py`)

- `--date-from`/`--date-to` ↔ `--days`: взаимоисключающие
- `--last N` ↔ любые даты: взаимоисключающие
- `--transcribe` без `--download-media`: предупреждение
- Реализовать через callback-валидацию Click

### 3.3. Режим `--all` и `--skip-unavailable` (новый файл → `tg_exporter_cli/commands/export_all.py` или расширение export.py)

- `export run --all`: экспорт всех чатов из `CliConfig.chats`
- `--skip-unavailable`: пропускать удалённые/заблокированные чаты
- Обработка `ChatNotFound`, `ChannelPrivate`
- Сохранение статуса `unavailable` в export_history

### 3.4. Режим `--resume` (доработка → `tg_exporter/services/export/export_orchestrator.py`)

- Читает `export_history.json` из папки чата
- Если файл есть и не прерван — стартует с `min_id = last_message_id`
- Если `"interrupted": true` — продолжает с последнего сообщения
- После экспорта обновляет `export_history.json`

### 3.5. ExportHistory: хранение в папке чата (→ `tg_exporter/services/export_history.py`)

Сейчас: `~/.tg_exporter/export_history.json` (глобальный).
Нужно: `{output_dir}/export_history.json` (на каждый чат).

Новый формат:
```json
{
  "last_message_id": 45678,
  "last_export_date": "2025-06-01T12:00:00+00:00",
  "total_exported": 12340,
  "status": "completed",
  "interrupted": false
}
```

API:
- `load(output_dir: Path) -> dict | None`
- `save(output_dir: Path, data: dict) -> None`
- `mark_interrupted(output_dir: Path) -> None`
- `mark_completed(output_dir: Path, last_id: int, total: int) -> None`
- `mark_unavailable(output_dir: Path) -> None`

### 3.6. Атомарная запись файлов (→ `tg_exporter/utils/file_utils.py`)

Создать утилиту `atomic_write(path, content)`:
- Пишет в `{path}.tmp`
- `os.fsync()`
- `os.replace(tmp, path)`

Применить в:
- `JsonExporter` — атомарный финальный файл
- `MarkdownExporter` — атомарные файлы частей
- `ExportHistory` — уже есть (доработать через общий хелпер)

### 3.7. Устойчивость к сбоям (→ `tg_exporter/services/export/export_orchestrator.py`)

- Проверка диска перед экспортом: `shutil.disk_usage()`
- Проверка диска каждые 50 медиафайлов
- При <100 MB — остановка с ошибкой
- Сохранение прогресса каждые 1000 сообщений в `export_history.json`
- При Ctrl+C: `export_history.json` с `"interrupted": true`
- Markdown: маркер `<!-- export in progress -->` убирается при завершении

### 3.8. Retry с экспоненциальной задержкой (→ `tg_exporter/utils/retry.py`)

```python
async def retry_async(fn, max_attempts=3, base_delay=2, max_delay=60):
    """Экспоненциальный backoff для сетевых операций."""
```

Применить в `ExportOrchestrator` для:
- `iter_messages()`
- `download_media()`

### 3.9. Команды `chats` (новый файл → `tg_exporter_cli/commands/chats.py`)

| Команда | Описание |
|---------|----------|
| `chats list` | Список всех чатов (из Telegram, через клиент) |
| `chats list --folder NAME` | Чаты в конкретной папке |
| `chats list --folders` | Только список папок |
| `chats list --search TERM` | Поиск по названию |
| `chats show --chat ID` | Информация о конкретном чате |
| `chats add --chat ID` | Добавить чат в `CliConfig.chats` |
| `chats add --folder NAME` | Добавить всю папку в `CliConfig.chats` |
| `chats remove --chat ID` | Убрать чат из `CliConfig.chats` |

### 3.10. Прогресс-бар (→ `tg_exporter_cli/output.py`)

- Использовать `rich.progress` если `rich` установлен
- Fallback: простой `\r` текст
- Показывать: сообщения, медиа, статус

### 3.11. `secure_permissions()` — единый хелпер (→ `tg_exporter/utils/file_utils.py`)

```python
def secure_permissions(path: Path, mode: int = 0o600) -> None:
    """Платформозависимая установка прав."""
```

Объединить дубликаты из:
- `app_config_repository.py`
- `profile_manager.py`
- `auth.py` (export-session)

### 3.12. Тесты Фазы 3

- `tests/unit/test_export_history.py` — расширить: per-chat storage, interrupted/completed/unavailable статусы
- `tests/unit/test_retry.py` — retry логика
- `tests/unit/test_file_utils.py` — atomic_write, secure_permissions
- `tests/integration/test_export_command.py` — расширить: все новые опции, валидация флагов, --all, --skip-unavailable, --resume
- `tests/integration/test_chats_command.py` — команды chats (новый файл)

---

## Фаза 4: Конфигурация, профили и удаление десктопа

### 4.1. Расширение CliConfig (→ `tg_exporter_cli/hosting/cli_config.py`)

Новые поля:
```python
@dataclass
class CliConfig:
    version: int = 1
    api_id: str = ""
    default_profile: str = "default"

    # Список чатов для быстрого доступа
    chats: list[ChatEntry] = field(default_factory=list)

    # Настройки по умолчанию для экспорта
    default_format: str = "both"          # json | markdown | both
    default_words_per_file: int = 50000
    default_download_media: bool = False
    default_transcribe: bool = False
    default_analytics: bool = False

    # Транскрипция
    transcription_provider: str = "local"
    transcription_model: str = "base"
    transcription_language: str = "multi"

    # Источник секретов: chain | env | keyring
    secrets_source: str = "chain"

    # Логирование
    log_level: str = "INFO"
    log_file: str = ""

    # Retry / rate limit (уже есть)
    retry_max_attempts: int = 3
    ...
```

Новая модель:
```python
@dataclass
class ChatEntry:
    name: str
    id: int
```

Обновить `load_cli_config()`/`save_cli_config()` в `cli_config_repository.py`.

### 4.2. Команды `config` (новый файл → `tg_exporter_cli/commands/config_cmd.py`)

| Команда | Описание |
|---------|----------|
| `config show` | Показать текущий конфиг |
| `config set KEY VALUE` | Установить значение |
| `config path` | Показать путь к конфиг-файлу |

### 4.3. Команды `profile` (новый файл → `tg_exporter_cli/commands/profile.py`)

| Команда | Описание |
|---------|----------|
| `profile list` | Список профилей |
| `profile add --phone --api-id --api-hash` | Добавить профиль |
| `profile remove --phone` | Удалить профиль |
| `profile switch --phone` | Переключить активный профиль |

### 4.4. Удаление десктопного кода

| Что удалить | Причина |
|------------|---------|
| `tg_exporter/ui/` (весь пакет) | Десктопный UI не нужен |
| `tg_exporter/utils/worker.py` | BackgroundWorker/EventDispatcher — только для GUI |
| `main.py` (корень) | Старая точка входа GUI |
| `tg_exporter/telegram/client.py` | Если есть — старый клиент без абстракции |

Из `requirements.txt` убрать:
- `customtkinter`
- `PySocks` (проверить использование)

### 4.5. Тесты Фазы 4

- `tests/integration/test_config_command.py` — config show/set/path
- `tests/integration/test_profile_command.py` — profile list/add/remove/switch

---

## Порядок реализации

1. **3.11** `secure_permissions()` + `atomic_write()` — базовые утилиты
2. **3.5** `ExportHistory` — хранение в папке чата, новый API
3. **3.8** `retry_async()` — retry с backoff
4. **3.1+3.2** Расширение CLI-опций `export` + валидация
5. **3.4+3.7** `--resume` + устойчивость к сбоям
6. **3.3** `--all` + `--skip-unavailable`
7. **3.9** Команды `chats`
8. **3.10** Прогресс-бар
9. **3.12** Тесты Фазы 3
10. **4.1** Расширение `CliConfig`
11. **4.2** Команды `config`
12. **4.3** Команды `profile`
13. **4.4** Удаление десктопного кода
14. **4.5** Тесты Фазы 4

---

## Дизайн-решения

- **ExportHistory** меняет API с `{peer_id: message_id}` на `{output_dir}/export_history.json` с метаданными. Старый формат несовместим — миграция не требуется (Phase 2 — MVP, данных нет).
- **Прогресс-бар**: `rich` — опциональная зависимость. Если не установлен — текстовый fallback без ошибки.
- **Валидация флагов**: через Click callback, не через `MutuallyExclusiveOption` (меньше магии, понятнее).
- **Retry**: применяется ТОЛЬКО к сетевым операциям (iter_messages, download_media). Не к логике.
- **ChatEntry**: простая frozen dataclass.
- **Удаление кода**: физическое удаление файлов с коммитом "remove deprecated desktop UI code".
