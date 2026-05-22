"""Заглушки для реакций (Reaction, ReactionResult, MessageReactions)."""

from __future__ import annotations


class FakeReaction:
    """Заглушка Reaction (эмодзи)."""

    def __init__(self, emoticon: str = "") -> None:
        self.emoticon = emoticon


class FakeReactionResult:
    """Заглушка ReactionResult (реакция + количество)."""

    def __init__(self, reaction: FakeReaction | None = None, count: int = 0) -> None:
        self.reaction = reaction or FakeReaction()
        self.count = count


class FakeReactions:
    """Заглушка message.reactions (MessageReactions)."""

    def __init__(self, results: list[FakeReactionResult] | None = None) -> None:
        self.results = results or []
