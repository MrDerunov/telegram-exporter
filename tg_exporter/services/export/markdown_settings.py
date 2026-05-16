"""
MarkdownSettings — настройки форматирования Markdown-экспорта.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


class ConfigValidationError(ValueError):
    """Ошибка валидации конфигурации."""
    pass


DATE_FORMATS = ("DD.MM.YYYY", "YYYY-MM-DD", "MM/DD/YYYY")


@dataclass
class MarkdownSettings:
    words_per_file: int = 50_000
    date_format: str = "DD.MM.YYYY"
    include_timestamps: bool = True
    include_author: bool = True
    include_replies: bool = True
    include_reactions: bool = False
    include_polls: bool = False
    include_forwarded: bool = True
    plain_text: bool = True

    def validate(self) -> None:
        if self.words_per_file < 1000:
            raise ConfigValidationError("words_per_file must be >= 1000")
        if self.date_format not in DATE_FORMATS:
            raise ConfigValidationError(
                f"date_format must be one of {DATE_FORMATS}, got {self.date_format!r}"
            )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> MarkdownSettings:
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})
