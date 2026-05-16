"""
AnalyticsResult — результат сбора аналитики.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .author_stats import AuthorStats


@dataclass
class AnalyticsResult:
    """Результат сбора аналитики."""
    authors: list[AuthorStats] = field(default_factory=list)   # отсортированы по убыванию
    activity: dict[str, int] = field(default_factory=dict)     # date → count
