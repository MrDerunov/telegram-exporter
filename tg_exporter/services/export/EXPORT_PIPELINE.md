# Export Pipeline — оркестратор, конвертер, экспортёры

Объединяет все этапы экспорта: получение сообщений, конвертацию, запись, медиа, транскрипцию, аналитику.

## ExportOrchestrator

Главный координатор. Запускается в фоновом потоке, взаимодействует через callback.

**Жизненный цикл:**
```
run(dialog, task, token, progress, callback)
  ├─ Подготовка директории, подсчёт сообщений
  ├─ Предзагрузка транскрибера
  ├─ Цикл по сообщениям:
  │   ├─ Проверка отмены (CancellationToken)
  │   ├─ Фильтры: дата, авторы, топик, лимит
  │   ├─ converter.message_to_export() → ExportMessage
  │   ├─ Транскрипция / запись в экспортёры / аналитика / медиа
  │   └─ Прогресс каждые 20 сообщений
  ├─ Финализация экспортёров
  ├─ Сохранение ExportHistory (для --resume)
  └─ Событие export_done
```

**Фильтры:** `date_from`/`date_to`, `topic_id`, `author_filter`, `message_limit`, `last_exported_id` (инкрементальный).

## Converter
Единственная точка интеграции с Telethon. `message_to_export()` → `ExportMessage`.
Извлекает: id, type, date, author, text, links, reactions, polls, media type, topics, forwards, views.

## ExportMessage
Иммутабельный dataclass. Чистые Python-типы, никаких ссылок на Telethon.
Все downstream-сервисы работают только с этой моделью.

## ExportTask
Иммутабельные параметры задачи: `chat_id`, `output_path`, `format`, `date_from`/`date_to`, `topic_id`,
`download_media`, `transcribe_audio`, `collect_analytics`, `author_filter`, `incremental`, `message_limit`, `words_per_file`.

## ExportProgress
Изменяемый объект для отслеживания прогресса: статус, счётчики, тайминг, ETA, warnings, output_files.

## Экспортёры

Наследуются от `BaseExporter` (ABC). Контракт: `open()` → `write(msg)` → `finalize()` → `close()`.

- **JsonExporter** — потоковая запись в `result.json`. При отмене дописывает закрывающие скобки.
- **MarkdownExporter** — разбивка по `words_per_file` слов. Форумные топики с индексом и навигацией. Настройки через `MarkdownSettings`.

## ExportHistory
Сервис истории экспорта. Хранит `last_exported_id` для каждого чата. Используется для `--resume`.
