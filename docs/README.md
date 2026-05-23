# Документация Telegram Exporter

Консольная утилита для экспорта чатов Telegram в JSON и Markdown.

## Общее

- **[Архитектура](ARCHITECTURE.md)** — обзор архитектуры, слои, ключевые принципы, поток данных, хранение конфигов
- **[Core Layer](../tg_exporter/services/telegram/ARCHITECTURE.md)** — аутентификация, клиент, профили
- **[Export Pipeline](../tg_exporter/services/export/EXPORT_PIPELINE.md)** — оркестратор, конвертер, экспортёры
- **[Transcription](../tg_exporter/services/transcription/ARCHITECTURE.md)** — Whisper, Deepgram

## Команды

| Группа | Назначение |
|--------|-----------|
| **[auth](commands/auth.md)** | Аутентификация в Telegram: вход, выход, проверка сессии, экспорт сессии |
| **[export](commands/export.md)** | Экспорт сообщений из чатов в JSON и Markdown |
| **[chats](commands/chats.md)** | Просмотр и управление списком чатов для экспорта |
| **[config](commands/config.md)** | Управление конфигурацией CLI |
| **[doctor](commands/doctor.md)** | Диагностика окружения |
| **[version](commands/version.md)** | Информация о версии утилиты |

## Быстрый старт

```bash
# Установка
pip install -e ".[dev]"

# Инициализация конфига
tg-exporter config init

# Логин в профиль
tg-exporter auth login

# Просмотр доступных чатов
tg-exporter chats list

# Экспорт одного чата
tg-exporter export --chat username_or_id --format both

# Экспорт всех чатов из конфига
tg-exporter export --all
```
