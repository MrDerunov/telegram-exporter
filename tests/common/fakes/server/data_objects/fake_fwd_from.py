"""Заглушка message.fwd_from (MessageFwdHeader)."""

from __future__ import annotations


class FakeFwdFrom:
    def __init__(
        self,
        from_name: str | None = None,
        from_id: int | None = None,
        channel_post: int | None = None,
    ) -> None:
        self.from_name = from_name
        self.from_id = from_id
        self.channel_post = channel_post
