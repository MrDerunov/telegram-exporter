"""
JsonExporter — потоковая запись сообщений в JSON.

Пишет в файл инкрементально (без накопления в памяти).
Совместим с текущим форматом result.json.
"""

from __future__ import annotations

import json
from typing import IO

from .base_exporter import BaseExporter
from tg_exporter.services.export.models.export_message import ExportMessage


class JsonExporter(BaseExporter):
    """
    Создаёт файл result.json вида:
    {
      "name": "Chat Name",
      "topic": "Topic Title",   // опционально
      "messages": [
        { ... },
        { ... }
      ]
    }

    Сообщения в массиве идут в хронологическом порядке (от старых к новым).
    """

    def __init__(self, include_views: bool = True) -> None:
        super().__init__()
        self._include_views = include_views
        self._messages: list[dict] = []
        self._output_path: str | None = None

    def _open(self) -> None:
        self._output_path = self._path("result.json")
        self._messages = []

    def write(self, msg: ExportMessage) -> None:
        d = msg.to_dict()
        if not self._include_views:
            d.pop("views", None)
            d.pop("forwards", None)
        self._messages.append(d)

    def finalize(self) -> list[str]:
        if self._output_path:
            self._messages.reverse()
            self._write_file(self._output_path)
            self._register(self._output_path)
        return self.output_files

    def close(self) -> None:
        """При отмене пишет накопленные сообщения, чтобы частичный экспорт
        остался валидным JSON."""
        if self._output_path and self._messages:
            self._messages.reverse()
            self._write_file(self._output_path)
        if self._output_path:
            self._register(self._output_path)

    def _write_file(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write('{\n  "name": ' + json.dumps(self._chat_name, ensure_ascii=False))
            if self._topic_title:
                f.write(',\n  "topic": ' + json.dumps(self._topic_title, ensure_ascii=False))
            f.write(',\n  "messages": [\n')

            for i, d in enumerate(self._messages):
                if i > 0:
                    f.write(",\n")
                json.dump(d, f, ensure_ascii=False)

            f.write('\n  ]\n}\n')
