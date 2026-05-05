"""
Render-функции для аналитики: render_top_authors и render_activity.
"""

from __future__ import annotations

import datetime

from .models import AnalyticsResult


def render_top_authors(result: AnalyticsResult, words_per_file: int = 50_000) -> list[str]:
    """
    Рендерит аналитику по авторам в список Markdown-строк.
    Каждый элемент — содержимое одного файла (разбивка по словам).
    """
    if not result.authors:
        return []

    summary_lines = [
        "# Топ авторов",
        "",
        "## Список участников",
        "",
    ]
    for a in result.authors:
        display = f"{a.name} (@{a.username})" if a.username else a.name
        summary_lines.append(f"- {display} — {a.message_count}")
    summary_lines.append("")

    summary_text = "\n".join(summary_lines)

    author_blocks: list[tuple[str, int]] = []
    for a in result.authors:
        display = f"{a.name} (@{a.username})" if a.username else a.name
        lines = [f"## {display} — {a.message_count}", ""]
        for entry in a.messages:
            if entry:
                lines.append(entry)
                lines.append("")
        block = "\n".join(lines)
        author_blocks.append((block, len(block.split())))

    parts: list[str] = []
    current = summary_text
    current_words = len(summary_text.split())

    for block, block_words in author_blocks:
        if current_words + block_words > words_per_file and current.strip() != summary_text.strip():
            parts.append(current)
            current = ""
            current_words = 0
        current = (current + "\n" + block) if current else block
        current_words += block_words

    if current.strip():
        parts.append(current)

    return [p.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n" for p in parts]


def render_activity(result: AnalyticsResult) -> str:
    """Рендерит активность по дням в Markdown-строку."""
    if not result.activity:
        return ""

    weekday_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    lines = [
        "# Активность по дням",
        "",
        "| Дата | День недели | Сообщений |",
        "| --- | --- | --- |",
    ]
    for day in sorted(result.activity.keys()):
        weekday = ""
        try:
            dt = datetime.date.fromisoformat(day)
            weekday = weekday_names[dt.weekday()]
        except Exception:
            pass
        lines.append(f"| {day} | {weekday} | {result.activity[day]} |")

    total = sum(result.activity.values())
    hot = sorted(result.activity.items(), key=lambda x: x[1], reverse=True)[:3]
    if hot:
        lines += ["", "## Самые горячие дни", ""]
        for day, cnt in hot:
            weekday = ""
            try:
                dt = datetime.date.fromisoformat(day)
                weekday = f" ({weekday_names[dt.weekday()]})"
            except Exception:
                pass
            lines.append(f"- {day}{weekday}: {cnt}")
        lines += ["", f"Всего сообщений: {total}"]

    return "\n".join(lines).replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"
