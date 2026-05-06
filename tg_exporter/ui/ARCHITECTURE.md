# UI Layer — десктопный интерфейс

## Назначение

UI Layer реализует графический интерфейс на customtkinter (Tkinter-обёртка). Не содержит бизнес-логики — только отображение, ввод данных и делегирование действий в фоновый поток.

## Компоненты

### App (`ui/app.py`)

Главный контроллер приложения. Владеет всеми сервисами и управляет навигацией.

**Обязанности:**
- Инициализация сервисов (Config, Credentials, Client, Auth, Profiles, Worker)
- Навигация между экранами: `show_login()` ↔ `show_chats()`
- Обработка UI Event-очереди (polling каждые 80 мс)
- Делегирование действий в фоновый поток через `_worker.submit()`
- Управление экспортом: `start_export()`, `cancel_export()`, `export_current_folder()`

**НЕ содержит:** бизнес-логику, прямые Telegram-вызовы, код экспорта.

**Навигация:**
```
┌─ LoginView ──────────────────────────────────┐
│  phone → code → 2FA → success → ChatListView │
└──────────────────────────────────────────────┘
                                                  ┌─────────────────────┐
Действия на ChatListView:                         │    ExportModal      │
  - Поиск чатов                                   │  (настройки +       │
  - Фильтр по папке                               │   прогресс)         │
  - Фильтр по периоду                              └─────────────────────┘
  - Кнопка «Экспорт» → ExportModal                ┌─────────────────────┐
  - Кнопка «Экспорт папки»                        │   SettingsModal     │
  - Кнопка «Настройки» → SettingsModal            └─────────────────────┘
  - Кнопка «Аккаунт ▾» → меню профилей            ┌─────────────────────┐
  - Кнопка «+ Аккаунт» → AddAccountModal          │   AddAccountModal   │
  - Кнопка «Инструкция» → HelpModal               └─────────────────────┘
                                                  ┌─────────────────────┐
                                                  │     HelpModal       │
                                                  └─────────────────────┘
```

### Views (`ui/views/`)

Каждый view — отдельный `CTkFrame` или `CTkToplevel`:

| View              | Тип       | Назначение                                  |
|-------------------|-----------|---------------------------------------------|
| `LoginView`       | CTkFrame  | Экран входа: api_id, api_hash, phone, code  |
| `ChatListView`    | CTkFrame  | Основной экран: список чатов, фильтры       |
| `ExportModal`     | CTkToplevel | Окно экспорта: опции + прогресс            |
| `SettingsModal`   | CTkToplevel | Настройки: транскрипция, Markdown           |
| `ApiKeysModal`    | CTkToplevel | Управление API-ключами                      |
| `AddAccountModal` | CTkToplevel | Добавление нового Telegram-аккаунта         |
| `HelpModal`       | CTkToplevel | Инструкция по использованию                 |

### Components (`ui/components/`)

Переиспользуемые виджеты:

| Компонент            | Назначение                                     |
|----------------------|------------------------------------------------|
| `AppButton`          | Кастомная кнопка (primary/secondary/ghost/danger) |
| `AppEntry`           | Поле ввода с placeholder, валидацией и ошибкой |
| `ExportProgressWidget` | Кастомный прогресс-бар с метками и статусом |

### Theme (`ui/theme.py`)

Единая дизайн-система. Все цвета, шрифты, отступы — строго отсюда.

- **Режим:** System (автоопределение light/dark)
- **Шрифты:** Segoe UI (Windows) / SF Pro (macOS) / Helvetica (Linux)
- **Цвета:** кортежи `(light, dark)`, функция `pick(key)` возвращает текущий
- **Токены:** RADIUS, SPACING, WIDGET — константы для всех размеров

Нигде в UI нет хардкода цветов или шрифтов.

## Событийная модель (`utils/worker.py`)

### BackgroundWorker

Один фоновый daemon-поток. Задачи выполняются последовательно через `queue.Queue`.

```
UI Thread                      Background Thread
   │                                 │
   │── submit(fn, *args) ──────────→ │ Выполнить fn(args)
   │                                 │
   │←──── put_event(type, payload) ─ │ Отправить результат
   │                                 │
   │── poll_events() (каждые 80ms)   │
```

**События (UIEvent = tuple[str, Any]):**

| Тип события              | Payload       | Откуда              |
|--------------------------|---------------|---------------------|
| `login_success`          | None          | AuthService         |
| `code_sent`              | None          | AuthService         |
| `login_error`            | str           | AuthService         |
| `login_2fa`              | None          | AuthService         |
| `logout_done`            | None          | AuthService         |
| `profile_switched`       | Profile       | App                 |
| `chats_loaded`           | list[Dialog]  | App._bg_load_chats  |
| `folders_loaded`         | list[str]     | App._bg_load_chats  |
| `export_start`           | (name, total) | ExportOrchestrator  |
| `export_progress`        | (count, total)| ExportOrchestrator  |
| `export_status`          | str           | ExportOrchestrator  |
| `export_done`            | (dir, files)  | ExportOrchestrator  |
| `export_error`           | str           | ExportOrchestrator  |
| `export_cancelled`       | None          | ExportOrchestrator  |
| `folder_progress`        | (i, n, name)  | App                 |
| `folder_done`            | int           | App                 |
| `error`                  | str           | Разные              |
| `worker_error`           | traceback     | BackgroundWorker    |

### EventDispatcher

Регистрирует обработчики событий и диспетчеризует их.

```
dispatcher.on("export_start", self._on_export_start)
dispatcher.on("export_progress", self._on_export_progress)
...

# В polling loop:
for event_type, payload in worker.poll_events():
    dispatcher.dispatch(event_type, payload)
```

Альтернатива длинному `if/elif` в polling loop.

## Экспорт папки (Folder Export)

App поддерживает пакетный экспорт всех чатов в выбранной папке Telegram:

- **Режимы:** «По чатам» (JSON+MD в поддиректориях), «Один .md на чат» (плоские MD), «Один .md на папку» (все чаты в одном файле)
- Выполняется последовательно: после завершения одного чата запускается следующий
- Поддерживает отмену всей цепочки через CancellationToken

## Состояние приложения

App хранит состояние в атрибутах:

| Поле                | Тип     | Описание                                  |
|---------------------|---------|-------------------------------------------|
| `config`            | AppConfig | Текущие настройки (без секретов)         |
| `credentials`       | CredentialsManager | Работа с Keyring                   |
| `_profiles`         | ProfileManager | Мульти-аккаунты                       |
| `_all_dialogs`      | list    | Кешированный список чатов                 |
| `_folder_peers`     | dict    | ID чатов по папкам                        |
| `_current_folder`   | str     | Выбранная папка                           |
| `_date_period_days` | int     | Выбранный период (0 = всё время)          |
| `_token`            | CancellationToken | Токен отмены текущего экспорта       |
