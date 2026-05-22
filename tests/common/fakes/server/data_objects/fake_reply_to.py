"""Заглушка message.reply_to (MessageReplyHeader)."""

from __future__ import annotations


class FakeReplyTo:
    def __init__(
        self,
        top_msg_id: int | None = None,
        reply_to_top_id: int | None = None,
        forum_topic: bool | None = None,
    ) -> None:
        self.top_msg_id = top_msg_id
        self.reply_to_top_id = reply_to_top_id
        self.forum_topic = forum_topic
