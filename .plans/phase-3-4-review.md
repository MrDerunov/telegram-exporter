# Ревью Фаз 3+4: Полноценный экспорт, чаты, конфигурация, профили

## Общая оценка: 🔴

Реализован большой объём функциональности, но есть несколько критичных багов (profile.py полностью неработоспособен, loop-баг в chats/export, chat_id=0 fallback), которые приведут к падению в рантайме. Требуется исправление перед использованием.

---

## Критичные (🔴) — упадут в рантайме

### 1. `profile.py` — полностью неработоспособен (4 бага)

**1a. `profile.py:26` — `profile_manager.get_all()` не существует**
- `ProfileManager` имеет метод `list()`, не `get_all()`. → `AttributeError` в рантайме.

**1b. `profile.py:56` — `profile_manager.add(phone, api_id, api_hash, name)` не существует**
- `ProfileManager` имеет `add_or_update(phone, api_id, session_string, display_name="", set_active=True)` — другие параметры и обязательный `session_string`.
- Для нового профиля (ещё без сессии) нужно передавать `session_string=""`.

**1c. `profile.py:100` — `client_manager.use_session(profile.session)` — два бага в одной строке**
- `use_session()` есть у `TelethonClientManager`, но НЕ в интерфейсе `ITelegramClientManager`. Переменная `client_manager` типизирована как `ITelegramClientManager` → `AttributeError`.
- `Profile` — frozen dataclass с полями `phone`, `display_name`, `api_id`. Поля `session` нет → второй `AttributeError`.

**1d. `profile.py:4` — неиспользуемый `import asyncio`**

### 2. `chats.py` + `export.py` — loop-баг: `run_until_complete` на работающем loop

Паттерн в `chats.py:29,90,133` и `export.py:258`:
```python
loop = asyncio.get_event_loop() if asyncio.get_event_loop().is_running() else asyncio.new_event_loop()
```
Если event loop УЖЕ работает, `get_event_loop()` возвращает его, но затем `loop.run_until_complete()` падает с `RuntimeError: This event loop is already running`.

**Правильный подход:** уже существует `tg_exporter_cli.utils.async_runner.run_async()` — его и нужно использовать везде вместо ручного создания loop.

### 3. `export.py:207-211` — `chat_id = 0` fallback ломает поиск по username

```python
try:
    chat_id = int(chat)
except ValueError:
    chat_id = 0  # username — поломано
```
При `chat="@channel"` → `chat_id=0`. Затем `str(d.id) == str(chat_id)` может случайно совпасть с диалогом с id=0, или не совпасть ни с чем → используется `_fallback_dialog` с фейковым объектом, на котором `c.iter_messages()` упадёт.

### 4. `export.py:266-268` — `_fallback_dialog` создаёт нерабочий диалог

Создаётся через `type()` без реальной Telegram-entity. При передаче в `c.iter_messages(dialog)` Telethon упадёт.

### 5. `export.py:140` — все ошибки считаются «unavailable» при `--skip-unavailable`

```python
except SystemExit as e:
    if e.code != 0 and skip_unavailable:
        click.echo(f"  ⚠ Пропущен (недоступен)")
        continue
    raise
```
`_run_export` кидает `SystemExit(1)` при ЛЮБОЙ ошибке (сеть, диск, авторизация), а не только при недоступном чате. С `--skip-unavailable` все ошибки молча пропускаются.

### 6. `retry.py:37` — `raise last_exc` когда `last_exc is None`

При `max_attempts=0` цикл не выполняется, `last_exc` остаётся `None`, `raise None` → `TypeError`. Нужна защита: `if last_exc is None: return` или валидация `max_attempts >= 1`.

---

## Важные (🟠)

### 7. `cli_config_repository.py:84-89` — дублирует `atomic_write`, без `fsync`

Метод `save_cli_config()` вручную делает `open(tmp, "w")` + `os.replace(tmp, path)`, хотя уже есть `atomic_write()` в `file_utils.py`. При этом пропущен `os.fsync()` → при крэше запись может потеряться.

### 8. `export_history.py:40` — ленивый импорт внутри метода

```python
def save(output_dir, data):
    from tg_exporter.utils.file_utils import atomic_write
```
Импорт внутри тела метода — должен быть на уровне модуля. `file_utils` не создаёт циклических зависимостей.

### 9. `retry.py` — сигнатура: `*args` неприменима с keyword-параметрами

```python
async def retry_async(fn, max_attempts=3, base_delay=2.0, max_delay=60.0, *args, **kwargs):
```
Нельзя вызвать `retry_async(fn, max_attempts=5, arg1)` — `*args` не может следовать за keyword-аргументом. Параметры `*args`/`**kwargs` фактически бесполезны. Лучше убрать их и использовать `functools.partial` или лямбду на стороне вызова.

### 10. `export_orchestrator.py:17` — неиспользуемый импорт `get_peer_id`

После замены `self._history.set_last_id(peer_id, ...)` на `mark_completed(export_dir, ...)` импорт `from telethon.utils import get_peer_id` стал мёртвым кодом.

### 11. `export_orchestrator.py:266` — `import shutil` внутри цикла

Импорт внутри тела цикла `for msg in c.iter_messages(...)` — должен быть наверху файла.

---

## Мелкие (💡)

### 12. `auth.py:1` — нет `from __future__ import annotations`

AGENTS.md требует во всех Python-файлах. Файл модифицировался, но директива не добавлена.

### 13. `export.py` — `_run_export` >100 строк, смешивает CLI-вывод и бизнес-логику

Функция и создаёт диалог, и форматирует вывод. По component architecture стоит разделить.

### 14. `config_cmd.py` — retry-поля типизированы как `int`, но задержки логичнее `float`

`retry_delay_seconds`, `retry_max_delay_seconds` — `int` в CliConfig. Меньше гибкости (нельзя указать 1.5 сек).

### 15. `file_utils.py:17-20` — `except OSError: pass` глотает все ошибки

В `secure_permissions()` все ошибки прав доступа молча игнорируются. Отладка проблем с правами будет невозможна.

### 16. `chats.py` — `get_dialogs()` без таймаута

Если Telegram недоступен, вызов `client.get_dialogs()` зависнет навсегда.

### 17. `export.py:123` — поиск диалога по имени неоднозначный

```python
if getattr(d, "name", "") == chat or getattr(d, "title", "") == chat:
```
Если несколько диалогов имеют одинаковое имя (например, два пользователя "Иван"), будет выбран первый попавшийся.

### 18. `app_config_repository.py` — возможно мёртвый код

Функции `load_app_config()` / `save_app_config()` не вызываются из `CliHost.build()` — там используется `cli_config_repository`. Возможно, этот файл больше не нужен.

---

## Итог

**Необходимо исправить перед использованием:**
1. `profile.py` — все 4 бага (get_all→list, add→add_or_update, use_session, profile.session)
2. `chats.py` + `export.py` — заменить ручной loop на `run_async()`
3. `export.py` — починить `chat_id=0` fallback
4. `export.py` — починить `_fallback_dialog` или убрать
5. `export.py` — различать ошибки «недоступен» и прочие в `--skip-unavailable`
6. `retry.py` — защита от `last_exc is None`

**Желательно исправить:**
7. `cli_config_repository.py` — использовать `atomic_write()`
8. Убрать мёртвый импорт `get_peer_id` из orchestrator
9. Ленивый импорт в `export_history.py`
10. `retry.py` — убрать `*args`, оставить только `**kwargs` или лямбду
