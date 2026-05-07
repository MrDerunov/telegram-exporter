"""
ExportFormat и ExportStatus — перечисления для формата и статуса экспорта.
"""

from __future__ import annotations

from enum import Enum, auto


class ExportFormat(str, Enum):
    JSON = "json"
    MARKDOWN = "markdown"
    BOTH = "both"


class ExportStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    DONE = auto()
    CANCELLED = auto()
    ERROR = auto()
