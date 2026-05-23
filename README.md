<div align="center">
  <h1>Telegram Exporter Cli</h1>
  <p><b>Консольная утилита для экспорта чатов и каналов Telegram в JSON и Markdown.</b></p>
  <p>
    <a href="https://github.com/MrDerunov/telegram-exporter/releases">
      <img src="https://img.shields.io/github/v/release/MrDerunov/telegram-exporter?style=flat-square" alt="Release">
    </a>
    <a href="https://opensource.org/licenses/MIT">
      <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square" alt="License: MIT">
    </a>
  </p>
</div>

> **Форк** от [morf3uzzz/telegram-exporter](https://github.com/morf3uzzz/telegram-exporter). Оригинал — десктопное GUI-приложение. Здесь оно пересобрано как консольная утилита с ядром (`tg_exporter`) и CLI-интерфейсом (`tg_exporter_cli`).

## Что умеет

- **Экспорт в JSON и Markdown** — сообщения с метаданными, реакциями, медиа, ссылками и опросами
- **Инкрементальный экспорт** — дозабирает только новые сообщения (`--resume`)
- **Фильтры:** период (`--days`, `--date-from/--date-to`), последние N сообщений (`--last`), топики форумов (`--topic-id`)
- **Массовый экспорт** всех чатов из конфига (`export --all --skip-unavailable`)
- **Скачивание медиа** — фото, видео, голосовые, документы раскладываются по папкам
- **Транскрипция голосовых и видео-кружков:** локально (Faster-Whisper) или через Deepgram
- **Аналитика:** топ авторов, активность по датам
- **Управление чатами:** просмотр по папкам Telegram, поиск, добавление в конфиг (`chats`)
- **CI/CD-режим:** auth export-session → secrets.env, auth verify для проверки сессии
- **Диагностика:** `doctor` — Python, конфиг, сессия, ffmpeg, место на диске

## Установка

### Готовые сборки

Скачай последнюю версию со [страницы релизов](https://github.com/MrDerunov/telegram-exporter/releases):

| Платформа | Файл |
|-----------|------|
| Linux (x86_64) | `tg-exporter-linux-x86_64.tar.gz` |
| macOS (Apple Silicon) | `tg-exporter-mac-arm64.tar.gz` |
| Windows (x86_64) | `tg-exporter-windows-x86_64.zip` |

### Из исходников

```bash
git clone https://github.com/MrDerunov/telegram-exporter.git
cd telegram-exporter
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
```

Python 3.11+.

## Первый запуск

```bash
# Получи api_id и api_hash на https://my.telegram.org → API development tools
tg-exporter auth login

# Проверить статус
tg-exporter auth status

# Диагностика окружения
tg-exporter doctor
```

Интерактивно вводятся: API ID, API Hash, номер телефона, код из Telegram, пароль 2FA (если есть).

## Где хранятся файлы

Директория конфигов определяется переменной окружения `TELEGRAM_EXPORTER_CONFIG_DIR`. Если переменная не задана — используется текущая рабочая директория.

```
<config_dir>/
├── config.json           # настройки (без секретов)
├── state.json            # состояние, профили, список чатов
├── secrets.json          # api_hash, сессия, ключи (если secrets_source=file)
├── .env                  # переменные окружения (опционально)
└── app.log               # лог
```

Секреты также можно хранить в keyring системы или в переменных окружения (`TG_EXPORTER_*`) — приоритет: env vars > .env > secrets.json.

Создать config.json с дефолтными значениями: `tg-exporter config init`.

## Примеры

```bash
# Экспорт чата в Markdown
tg-exporter export --chat @channel_name --format markdown

# Последние 7 дней с медиа и транскрипцией
tg-exporter export --chat -1001234567890 --days 7 --download-media --transcribe

# Тестовый экспорт: последние 100 сообщений
tg-exporter export --chat -1001234567890 --last 100

# Продолжить прерванный экспорт
tg-exporter export --chat -1001234567890 --resume

# Массовый экспорт всех чатов из конфига
tg-exporter export --all --skip-unavailable --format both

# Просмотр чатов по папкам Telegram
tg-exporter chats list
tg-exporter chats list --folder "Работа"
tg-exporter chats list --search "кот"

# Добавить чат в конфиг
tg-exporter chats add --chat -1001234567890

# CI/CD: экспорт сессии
tg-exporter auth export-session
tg-exporter auth verify
```

## Лицензия

MIT — см. [LICENSE](LICENSE).
