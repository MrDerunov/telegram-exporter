# План реализации Фазы 2: Команды и тесты (MVP)

> Ветка: `phase/2-commands-mvp`
> Исходный план: `cli-app-plan.md` §14, «Фаза 2»
> База: Фаза 1 влита в main (69 файлов, +1627 строк)

## Цель

Превратить 12 Click-заглушек в рабочие команды. AuthService и ExportOrchestrator уже адаптированы под `ITelegramClientManager`, контейнер собирает все зависимости. Осталось соединить Click-команды с сервисами и покрыть тестами.

## Анализ текущего кода

### Что уже готово (из Фазы 1)
- `Container` — собирает auth_service, profile_manager, orchestrator, client_manager, credentials, secret_provider
- `main.py` — Click группа с 12 командами-заглушками (`[TODO]`)
- `AuthService` — async-методы: `check_session()`, `send_code(phone)`, `verify_code(code)`, `verify_password(pwd)`, `logout()`
- `ExportOrchestrator` — принимает `ITelegramClientManager`, `AppConfig`, `ExportHistory`
- `FakeTelegramClient` — полная реализация ABC, предзагрузка данных
- `FakeTelegramClientManager` — фабрика для тестов
- `CliConfig` — YAML-конфиг с `version`, `retry.*`, `rate_limit.*`

### Что нужно сделать

## Задачи (4 подзадачи для субагентов)

### Задача A: Реализовать auth-команды

**Файл:** `tg_exporter_cli/commands/auth.py` (новый)

Перенести логику из `main.py` auth-группы в отдельный файл.

**Реализовать 5 команд:**

1. **`auth login`** — интерактивный вход
   ```
   Options: --phone TEXT, --api-id TEXT, --api-hash TEXT, --profile TEXT
   ```
   - Создаёт Container
   - Если api_id/api_hash не в опциях — читает из конфига
   - Если не заданы — запрашивает интерактивно (click.prompt)
   - Вызывает `AsyncRunner.run(container.auth_service.send_code(phone))`
   - Запрашивает код подтверждения через `click.prompt`
   - Вызывает `verify_code()`, при 2FA — запрашивает пароль
   - Сохраняет сессию: `container.auth_service` → manager.save_session()
   - Выводит: «✅ Авторизован как @username»

2. **`auth status`** — проверка авторизации
   ```
   Options: --profile TEXT
   ```
   - Вызывает `check_session()`
   - Выводит: «✅ Авторизован как @username» или «❌ Не авторизован»

3. **`auth logout`** — выход
   ```
   Options: --profile TEXT  
   ```
   - Вызывает `logout()`
   - Выводит: «✅ Выполнен выход из аккаунта»

4. **`auth export-session`** — экспорт сессии
   ```
   Options: --output PATH (default: ./secrets.env)
   ```
   - Читает сессию из credentials
   - Пишет `secrets.env` с `TG_EXPORTER_API_ID`, `TG_EXPORTER_API_HASH`, `TG_EXPORTER_SESSION`
   - Права 0o600
   - Предупреждение: «⚠️ Файл содержит полный доступ к аккаунту»

5. **`auth verify`** — проверка для CI/CD
   ```
   Exit codes: 0 (валидна), 1 (невалидна), 2 (нет сессии)
   ```
   - Вызывает `check_session()`, без интерактива
   - Возвращает exit code

**Хелпер AsyncRunner:**
Т.к. AuthService методы async, а Click команды sync, нужен хелпер:
```python
# tg_exporter_cli/async_runner.py (новый)
import asyncio

class AsyncRunner:
    @staticmethod
    def run(coro):
        return asyncio.run(coro)
```

### Задача B: Реализовать export-команду (базовый MVP)

**Файл:** `tg_exporter_cli/commands/export.py` (новый)

**`export run`** — базовый экспорт одного чата
```
Options:
  --chat TEXT (required)  ID или username
  --output PATH           Директория (default: ./export/{chat_name})
  --format [json|markdown|both]  (default: both)
  --last INTEGER          Последние N сообщений (тестовый режим)
```

- Создаёт Container
- Формирует `ExportTask` с параметрами
- Вызывает `container.orchestrator.run(task, cancellation_token, progress_callback)`
- Выводит прогресс через `click.progressbar` или `rich.progress`
- После завершения: «✅ Экспорт завершён: N сообщений → {output_dir}»

**Hint:** Orchestrator.run() синхронный? Проверить сигнатуру. Если async — использовать AsyncRunner.

### Задача C: Реализовать version и doctor

**Файлы:** `tg_exporter_cli/commands/version.py`, `tg_exporter_cli/commands/doctor.py` (новые)

**`version`:**
```
tg-exporter 1.0.0 (python 3.12, Linux x86_64)
```
Уже есть базовая реализация, дополнить информацией о платформе.

**`doctor`:**
Диагностика окружения:
```
✅ Python 3.12.3
✅ Конфиг: ~/.tg_exporter/cli_config.yaml (OK)
⚠️ Keyring: недоступен (headless)
✅ Сессия: валидна (@username)
✅ ffmpeg: 7.0.2
⚠️ Место на диске: 2.1 GB свободно
```
Проверяет: Python version, конфиг (path + валидность), keyring доступность, сессию (через check_session), ffmpeg (shutil.which), свободное место (shutil.disk_usage).

### Задача D: Unit и integration тесты

**Файлы:**
- `tests/unit/test_converter.py` — конвертация Telethon → ExportMessage
- `tests/unit/test_export_history.py` — сохранение/загрузка export_history.json
- `tests/unit/test_secrets.py` — SecretProvider + все реализации
- `tests/unit/test_exporters.py` — JsonExporter, MarkdownExporter
- `tests/integration/test_auth_command.py` — auth login/status/logout/verify через CliRunner
- `tests/integration/test_export_command.py` — export через CliRunner + FakeTelegramClient

**Unit тесты:**
- `test_converter.py` — `message_to_export()` для всех типов сообщений
- `test_export_history.py` — load/save, инкрементальный min_id, interrupted флаг
- `test_secrets.py` — get/set/delete для всех 4 провайдеров, chain порядок, writable фильтр
- `test_exporters.py` — JsonExporter (структура JSON), MarkdownExporter (форматирование)

**Integration тесты:**
- `test_auth_command.py`:
  ```python
  def test_auth_status_not_authorized(cli_runner, container_with_fake_client):
      result = cli_runner.invoke(cli_main, ["auth", "status"])
      assert "Не авторизован" in result.output
  
  def test_auth_login_flow(cli_runner, container_with_fake_client):
      # симулируем успешный вход
      ...
  ```
- `test_export_command.py`:
  ```python
  def test_export_last_n_messages(cli_runner, container_with_fake_client):
      fake_client = container_with_fake_client.client_manager.create_client()
      fake_client.add_messages(-1001234, generate_messages(200))
      result = cli_runner.invoke(cli_main, ["export", "run", "--chat", "-1001234", "--last", "50"])
      assert result.exit_code == 0
      assert "Экспорт завершён" in result.output
  ```

**Фикстуры (обновить conftest.py если нужно):**
Добавить `cli_runner` фикстуру:
```python
@pytest.fixture
def cli_runner():
    from click.testing import CliRunner
    return CliRunner()
```

### Задача E: Рефакторинг main.py

Вынести команды из `main.py` в `tg_exporter_cli/commands/`:
- `tg_exporter_cli/commands/__init__.py`
- `tg_exporter_cli/commands/auth.py`
- `tg_exporter_cli/commands/export.py`
- `tg_exporter_cli/commands/version.py`
- `tg_exporter_cli/commands/doctor.py`

Оставить в `main.py` только регистрацию групп и импорт команд. Заглушки для chats/profile/config оставить как есть (будут в Фазе 3/4).

### Задача F: Сквозной сценарий на фейковом клиенте

Скрипт или тест, проверяющий полный цикл:
```python
def test_end_to_end(container_with_fake_client, tmp_path):
    fake_client = container_with_fake_client.client_manager.create_client()
    fake_client.set_authorized(True)
    fake_client.add_messages(-1001234, generate_messages(100))
    
    # Экспорт
    orchestrator = container_with_fake_client.orchestrator
    task = ExportTask(chat_id=-1001234, output_dir=tmp_path, format=ExportFormat.JSON)
    orchestrator.run(task, CancellationToken(), lambda s, o: None)
    
    # Проверка результата
    result_file = tmp_path / "result.json"
    assert result_file.exists()
    data = json.loads(result_file.read_text())
    assert len(data["messages"]) == 100
```

## Порядок выполнения

1. Ветка `phase/2-commands-mvp` уже создана
2. Запустить задачи A, B, C, D параллельно (4 субагента)
3. После завершения — задача E (рефакторинг main.py) — её делает агент C
4. После — задача F (сквозной сценарий)
5. Ревью всего кода фазы
6. Исправления по ревью
7. Merge в main
8. Перенести план в `.plans/done/`

## Критерии приёмки

- [ ] `tg-exporter auth login` — интерактивная аутентификация работает
- [ ] `tg-exporter auth status` — показывает статус
- [ ] `tg-exporter auth logout` — выходит из аккаунта
- [ ] `tg-exporter auth export-session` — создаёт secrets.env с 0o600
- [ ] `tg-exporter auth verify` — возвращает exit code 0/1/2
- [ ] `tg-exporter export run --chat X --last N` — базовый экспорт работает
- [ ] `tg-exporter version` — показывает версию и платформу
- [ ] `tg-exporter doctor` — диагностика окружения
- [ ] Unit-тесты на Converter, ExportHistory, Exporters, SecretProvider проходят
- [ ] Integration-тесты на auth и export через CliRunner проходят
- [ ] Сквозной сценарий на фейковом клиенте проходит
- [ ] Команды вынесены в `tg_exporter_cli/commands/`
