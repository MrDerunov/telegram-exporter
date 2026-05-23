# config — Управление конфигурацией

**Назначение:** Просмотр и изменение настроек CLI.

Конфигурация хранится в `config.json` в директории `$TELEGRAM_EXPORTER_CONFIG_DIR` (или текущей). Управляет поведением экспорта по умолчанию, параметрами ретраев, rate limiting и другими настройками.

## Команды

### `config show`

Показывает текущие значения всех полей конфига:
- API ID
- Формат экспорта, размер Markdown-файлов
- Флаги медиа, транскрипции, аналитики
- Источник секретов, уровень логирования
- Параметры ретраев и rate limiting

### `config set`

Устанавливает значение поля конфига.

Поддерживаемые ключи: `api_id`, `default_format`, `default_words_per_file`, `default_download_media`, `default_transcribe`, `default_analytics`, `secrets_source`, `log_level`, `transcription_provider`, `transcription_model`, `transcription_language`, `retry_max_attempts`, `retry_delay_seconds`, `retry_max_delay_seconds`, `rate_limit_media_download_delay_ms`, `rate_limit_message_fetch_delay_ms`.

```bash
tg-exporter config set default_format json
tg-exporter config set default_download_media true
```

### `config path`

Выводит абсолютный путь к файлу `config.json`.

### `config init`

Создаёт `config.json` со значениями по умолчанию.

- Если файла нет — создаёт новый
- Если файл есть — с флагом `--force` добавляет отсутствующие поля, не перезаписывая существующие

| Опция | Назначение |
|-------|-----------|
| `--force` / `-f` | Обновить существующий конфиг (добавить недостающие поля) |
