# Export Pipeline — оркестратор, конвертер, экспортёры

## Назначение

Export Pipeline объединяет все этапы экспорта: получение сообщений из Telegram, конвертацию в промежуточную модель, запись в выходные форматы, скачивание медиа, транскрипцию и аналитику.

## ExportOrchestrator (`services/export/export_orchestrator.py`)

Главный координатор процесса экспорта. Выполняется целиком в фоновом потоке, без взаимодействия с UI напрямую — только через callback.

**Жизненный цикл одного экспорта:**

```
run(dialog, task, token, progress, send_callback)
  │
  ├─ Подготовка директории экспорта
  ├─ Подсчёт сообщений
  ├─ Предзагрузка транскрибера (опционально, с прогрессом)
  ├─ Создание экспортёров (JSON / Markdown)
  ├─ Создание коллекторов (Analytics, MediaDownloader)
  │
  ├─ Основной цикл итерации по сообщениям:
  │   ├─ Проверка токена отмены
  │   ├─ Фильтр по дате / авторам
  │   ├─ Конвертация: message_to_export()
  │   ├─ Транскрипция голосовых/кружков (опционально)
  │   ├─ Запись в экспортёры
  │   ├─ Сбор аналитики
  │   ├─ Скачивание медиа (опционально)
  │   └─ Каждые 20 сообщений: событие export_progress
  │
  ├─ Финализация экспортёров → output_files
  ├─ Запись аналитики → top_authors.md, activity.md
  ├─ Сохранение ExportHistory (для инкрементального)
  ├─ Выгрузка модели транскрибера
  └─ Событие export_done
```

**События (через callback):**
- `export_start` — начало, имя чата и общее кол-во
- `export_progress` — текущий прогресс (каждые 20 сообщений)
- `export_status` — текущий статус (скачивание, транскрипция)
- `model_download_progress` — прогресс скачивания Whisper-модели
- `export_done` — (директория, список файлов)
- `export_error` — сообщение об ошибке
- `export_cancelled` — отмена пользователем

**Фильтры:**
- По дате: `date_from` / `date_to` (offset_date в Telethon iter_messages)
- По топику: `topic_id` (reply_to в iter_messages)
- По авторам: `author_filter` (sender_id)
- Инкрементальный: `min_id` (только сообщения с ID > последнего экспортированного)

## Converter (`telegram/converter.py`)

Единственная точка интеграции с Telethon. Преобразует Telethon `Message` в `ExportMessage`.

**Извлекаемые данные:**
- Базовые: id, type (message/service), date (ISO 8601)
- Автор: from_name, from_username, from_id
- Контент: text, links (MessageEntityTextUrl / MessageEntityUrl)
- Реакции: ReactionItem (emoji, count)
- Опросы: PollData (question, answers, total_voters)
- Медиа: MediaType (photo/video/voice/video_note/document/sticker/animation)
- Топики: topic_id, is_topic_message, is_forum_topic, topic_title
- Пересылка: forwarded_from
- Метаданные: views, forwards, reply_to_message_id

## Экспортёры (`services/export/exporters/`)

Все экспортёры наследуются от `BaseExporter` (ABC).

### BaseExporter (`services/export/exporters/base_exporter.py`)

**Контракт:**
1. `open(export_dir, chat_name, topic_title)` — инициализация
2. `write(msg: ExportMessage)` — запись одного сообщения
3. `finalize() → list[str]` — завершение, возвращает пути к файлам
4. `close()` — освобождение ресурсов (при отмене)

Экспортёры работают только с `ExportMessage`, без зависимости от Telethon.

**Утилита:** `sanitize_filename()` (`services/export/exporters/sanitize.py`) — безопасное имя файла (запрещённые символы, control chars, Windows reserved names, обход через `..`).

### JsonExporter (`services/export/exporters/json_exporter.py`)

Потоковая запись в JSON без накопления в памяти.

**Формат вывода (`result.json`):**
```json
{
  "name": "Chat Name",
  "topic": "Topic Title",
  "messages": [
    { "id": 1, "type": "message", "date": "...", "from": "...", "text": "..." },
    ...
  ]
}
```

**Особенности:**
- Инкрементальная запись: каждое сообщение пишется сразу в файл
- При отмене (`close()`) — дописывает закрывающие скобки, чтобы частичный экспорт остался валидным JSON
- Опционально исключает `views` и `forwards` через параметр `include_views`

### MarkdownExporter (`services/export/exporters/markdown_exporter.py`)

Запись сообщений в Markdown с разбивкой по файлам.

**Формат вывода:**
- `{chat_name}_part_1.md`, `_part_2.md`, ... — разбивка по `words_per_file` слов
- `{chat_name}_popular.md` — популярные сообщения (по реакциям, опционально)

**Структура сообщения:**
```
[DD.MM.YYYY HH:MM] **Author:** Текст сообщения

🔗 ссылки | Реакции: 👍×3 · ❤️×1
Транскрипция: текст голосового
```

**Форумы:** при наличии топиков в первом файле выводится индекс тем. Сообщения внутри топика помечаются HTML-комментариями для навигации.

**Настройки (`MarkdownSettings`):** формат даты, включение/отключение таймстемпов, авторов, реакций, опросов, реплаев, пересылок, plain_text режим.

## Параметры задачи (`ExportTask`)

Иммутабельный dataclass, создаётся один раз перед запуском:

- `chat_id`, `chat_name`, `output_path` — обязательные
- `format` — JSON / Markdown / BOTH
- `date_from`, `date_to` — фильтр по дате
- `topic_id`, `topic_title` — топик форума
- `download_media`, `collect_analytics`, `transcribe_audio` — флаги
- `author_filter` — фильтр по ID авторов
- `incremental`, `last_exported_id` — инкрементальный режим
- `words_per_file` — размер Markdown-файлов

## ExportProgress

Изменяемый объект (не frozen), обновляется в фоновом потоке, читается UI:

- Статус: PENDING → RUNNING → DONE / CANCELLED / ERROR
- Счётчики: total/processed/skipped messages, media_downloaded/failed
- Тайминг: started_at, finished_at, elapsed_seconds
- ETA: оставшееся время (оценка по прогрессу)
- Список warnings и финальный список output_files
