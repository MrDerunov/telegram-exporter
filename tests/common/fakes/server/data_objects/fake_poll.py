"""Заглушки для опросов (PollAnswer, Poll, PollAnswerVoters, PollResults, MessageMediaPoll)."""

from __future__ import annotations


class FakePollAnswer:
    """Заглушка PollAnswer."""

    def __init__(self, option: bytes = b"", text: str = "") -> None:
        self.option = option
        self.text = text


class FakePoll:
    """Заглушка Poll (опрос)."""

    def __init__(
        self,
        id: int = 0,
        question: str = "",
        answers: list[FakePollAnswer] | None = None,
    ) -> None:
        self.id = id
        self.question = question
        self.answers = answers or []


class FakePollResultEntry:
    """Заглушка PollAnswerVoters."""

    def __init__(self, option: bytes = b"", voters: int = 0) -> None:
        self.option = option
        self.voters = voters


class FakePollResults:
    """Заглушка PollResults."""

    def __init__(
        self,
        results: list[FakePollResultEntry] | None = None,
        total_voters: int | None = None,
    ) -> None:
        self.results = results or []
        self.total_voters = total_voters


class FakePollMedia:
    """Заглушка message.poll (MessageMediaPoll)."""

    def __init__(
        self,
        poll: FakePoll | None = None,
        results: FakePollResults | None = None,
    ) -> None:
        self.poll = poll
        self.results = results
