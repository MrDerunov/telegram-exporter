# Ревью Фазы 1: Абстракция клиента и базовая инфраструктура

## Общая оценка: ⚠️

Базовый скелет Фазы 1 собран: интерфейс, адаптер, провайдеры секретов, DI-контейнер, CLI-заглушки и фейки для тестов — всё на месте. Но **интерфейс не потребляется сервисами**: `AuthService` и `ExportOrchestrator` сменили тип на `TelegramClientInterface`, а внутри продолжают вызывать `get_client()` / `destroy()` — методы, которых нет в интерфейсе. Это критичное расхождение между сигнатурами и реальным API.

## Замечания

### Критичные (❌)

#### ❌ 1. `get_client()` и `destroy()` вызываются из сервисов, но не входят в интерфейс

**Файлы:** `tg_exporter/core/auth/auth_service.py`, `tg_exporter/core/orchestrator.py`

`ensure_connected()` из `TelegramClientManager` был заменён на `get_client()` из `TelethonClientAdapter`, но оба метода отсутствуют в `TelegramClientInterface`:

```python
# AuthService — 5 вызовов get_client(), 1 вызов destroy():
c = self._client.get_client()       # ⇐ не в интерфейсе!
self._client.destroy()              # ⇐ не в интерфейсе!

# ExportOrchestrator:
c = self._client.get_client()       # ⇐ не в интерфейсе!
```

`get_client()` объявлен в `TelethonClientAdapter` как «Compatibility bridge (не часть интерфейса)». При этом аннотации типов утверждают, что сервисы принимают `TelegramClientInterface`. На практике они **требуют** `TelethonClientAdapter`.

**Следствия:**
- `FakeTelegramClient` не имеет `get_client()` / `destroy()` → `container_with_fake_client` соберётся, но `auth_service.check_session()` упадёт с `AttributeError`
- При добавлении второго адаптера (например, Pyrogram) придётся дублировать эти compatibility-методы

**Рекомендация:** либо добавить `get_client()` в интерфейс с документированием что это временный compatibility bridge, либо (лучше) переписать `AuthService` на использование методов интерфейса (`send_code_request`, `sign_in`, `sign_in_password`, `connect`, `is_authorized`) и добавить `destroy` в интерфейс.

#### ❌ 2. Интерфейс не потребляется сервисами — абстракция не работает

Методы интерфейса `send_code_request`, `sign_in`, `sign_in_password` **не используются** ни в одном сервисе. AuthService получает сырой клиент через `get_client()` и вызывает Telethon-методы напрямую:

```python
# Фактическое использование (auth_service.py:76):
c = self._client.get_client()
c.send_code_request(phone)      # ⇐ Telethon напрямую, не через интерфейс

# Ожидаемое использование:
await self._client.send_code_request(phone)   # ⇐ через интерфейс
```

Аналогично `ExportOrchestrator._do_run()` получает сырой клиент и работает с ним напрямую (`c.iter_messages()`, `c.get_messages()`, `c.get_input_entity()`), полностью минуя интерфейсные методы `iter_messages()` и `get_dialogs()`.

**Рекомендация:** либо явно зафиксировать это как «осознанный технический долг на Фазу 1» в комментариях к коду, либо реализовать использование интерфейса хотя бы в AuthService.

### Важные (⚠️)

#### ⚠️ 3. `TelethonClientAdapter.save_session()` падает при отсутствии клиента

```python
def save_session(self) -> str:
    self._manager.save_session()
    if self._manager._client is not None:     # проверка есть
        return self._manager._client.session.save()
    return ""
```

Проверка `self._manager._client is not None` есть, но код доступа к приватному полю `_client` — хрупкий. Более того, если `_client is None`, метод возвращает `""`, а `TelegramClientManager.save_session()` внутри делает свою проверку и молча выходит. Это дублирование логики. Лучше делегировать сохранение сессии полностью в менеджер.

**Рекомендация:** добавить в `TelegramClientManager` метод `get_session_string() -> str`, возвращающий сохранённую сессию или `""`, и использовать его из адаптера.

#### ⚠️ 4. 11 команд вместо заявленных 12

План: «12 команд-заглушек». Реализовано: 11.

| Команда | Статус |
|---------|--------|
| `auth login` | ✅ |
| `auth status` | ✅ |
| `auth logout` | ✅ |
| `auth export-session` | ✅ |
| `auth verify` | ✅ |
| `export run` | ✅ |
| `chats list` | ✅ |
| `profile list` | ✅ |
| `config show` | ✅ |
| `version` | ✅ |
| `doctor` | ✅ |

**Рекомендация:** уточнить в плане — возможно, ожидалась `profile add` или `chats info`. Либо исправить число в плане на 11.

#### ⚠️ 5. Контейнер использует `CredentialsManager` (Keyring) вместо нового `SecretProvider`

```python
self.secret_provider = ChainSecretProvider([...])  # новый путь
self.credentials = CredentialsManager()             # старый путь (Keyring)
```

`CredentialsManager` жёстко завязан на Keyring и не использует `self.secret_provider`. Получается два параллельных механизма хранения секретов:
- `self.secret_provider` — для CLI (env vars, .env)
- `self.credentials` — для core (Keyring)

Это нормально для Фазы 1 (план явно говорит не менять `CredentialsManager`), но стоит добавить TODO-комментарий о миграции в будущих фазах.

**Рекомендация:** добавить `# TODO(phase-2): migrate CredentialsManager to SecretProvider` в `container.py`.

#### ⚠️ 6. `FakeTelegramClient` не поддерживает `get_client()` — conftest фикстура сломана для AuthService

```python
@pytest.fixture
def container_with_fake_client(fake_client, tmp_path) -> Container:
    return Container(..., telegram_client=fake_client)
```

`container.auth_service.check_session()` вызовет `self._client.get_client()` → `AttributeError` на `FakeTelegramClient`. Фикстура собирается без ошибок, но любое использование `auth_service` или `orchestrator` упадёт.

**Рекомендация:** либо добавить `get_client()`/`destroy()` в `FakeTelegramClient` (с пометкой что это compatibility), либо документировать что фикстура — только для тестов провайдеров/конфига в Фазе 1.

### Мелкие (💡)

#### 💡 7. `FakeTelegramClient`: async-методы без await

```python
async def connect(self) -> None:
    self.call_log.append("connect")  # нет await
```

План говорит «Все методы синхронные (возвращают готовые данные, не async)». Но все методы объявлены как `async`. Синхронные async-функции работают, но создают лишние корутины. В pytest-asyncio это требует `@pytest.mark.asyncio` для тестов.

**Рекомендация:** убрать `async` и сделать методы синхронными (план явно это предполагает), либо оставить async и добавить `await asyncio.sleep(0)` для имитации реального I/O.

#### 💡 8. `EnvFileSecretProvider.delete()` — молчаливый no-op

```python
def delete(self, key: str) -> None:
    # no-op: провайдер не пишет в .env
    pass
```

Ожидаемое поведение для `writable=False`, но стоит добавить docstring с пояснением (аналогично `set` с `NotImplementedError`).

#### 💡 9. `EnvFileSecretProvider`: `python-dotenv` проверяется внутри метода

Импорт `dotenv_values` делается внутри `_load()`, а не на уровне модуля. Это позволяет модулю импортироваться без `python-dotenv`, но маскирует отсутствие зависимости — `get()` будет молча возвращать `None` вместо ошибки импорта.

**Рекомендация:** добавить `logger.warning` при `ImportError`, либо вынести импорт на уровень модуля с понятным сообщением.

#### 💡 10. `CliConfig.save()` не обрабатывает ошибки записи

```python
def save(self, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ...
    with open(path, "w") as f:
        yaml.safe_dump(data, f, ...)
```

Нет try/except на случай отсутствия прав на запись, заполненного диска и т.п. `AppConfig.save()` (существующий) делает атомарную запись с fsync — стоит привести к тому же уровню.

#### 💡 11. `tg_exporter_cli/__init__.py` пустой

Файл существует (создан для пакета), но пустой. Можно экспортировать ключевые классы: `Container`, `CliConfig` для удобства `from tg_exporter_cli import Container`.

#### 💡 12. `KeyringSecretProvider` не импортируется в `container.py`

Импорт `KeyringSecretProvider` есть только в `tg_exporter_cli/secrets/__init__.py`. Контейнер его не использует (что правильно — план требует не подключать keyring по умолчанию ✅). Но для явной документации можно добавить закомментированную строку в контейнере:

```python
# KeyringSecretProvider() — не подключаем по умолчанию (headless)
```

## Проверка критериев приёмки

| Критерий | Статус |
|----------|--------|
| `TelegramClientInterface` ABC с async-методами | ✅ |
| `TelethonClientAdapter` реализует интерфейс, оборачивая `TelegramClientManager` | ✅ |
| `AuthService` принимает `TelegramClientInterface`, а не `TelegramClientManager` | ⚠️ Тип изменён, но вызываются методы не из интерфейса |
| `ExportOrchestrator` принимает `TelegramClientInterface`, а не `TelegramClientManager` | ⚠️ Тип изменён, но вызываются методы не из интерфейса |
| Все 4 SecretProvider'а реализованы с флагом `writable` | ✅ |
| `ChainSecretProvider` пишет только в writable | ✅ |
| `Container` собирает все зависимости | ✅ |
| `main.py` — Click группа с заглушками всех команд | ⚠️ 11 команд вместо 12 |
| `FakeTelegramClient` реализует ABC | ✅ |
| Тесты проходят | ⚠️ Не проверены (нет telethon/pytest в окружении) |
| Существующий код (UI, worker) не сломан | ✅ Не тронут |
| Keyring не подключается по умолчанию | ✅ |

## Итог

Фундамент заложен правильно: интерфейс, адаптер, провайдеры секретов и DI-контейнер соответствуют плану. Структура кода чистая, нейминг в snake_case, docstring на месте. 

**Главная проблема:** типовая замена `TelegramClientManager → TelegramClientInterface` сделана только на уровне аннотаций. Фактическое использование `get_client()` / `destroy()` нарушает контракт интерфейса и делает `FakeTelegramClient` несовместимым с `AuthService` и `ExportOrchestrator`.

**Рекомендуемое действие:** зафиксировать это как осознанный компромисс Фазы 1 (добавив TODO на переписывание сервисов в Фазе 2-3) и добавить `get_client()` / `destroy()` в `FakeTelegramClient` для работоспособности тестов, либо добавить эти методы в интерфейс как временные.

После исправления критичных замечаний — можно мёржить в main.
