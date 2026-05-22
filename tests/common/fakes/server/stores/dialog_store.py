"""Хранилище фейковых диалогов."""

from __future__ import annotations

from ..data_objects.fake_dialog import FakeDialog


class DialogStore:
    def __init__(self) -> None:
        self._dialogs: dict[int, FakeDialog] = {}

    def add_dialog(self, dialog: FakeDialog) -> None:
        self._dialogs[dialog.id] = dialog

    def get_dialog(self, peer_id: int) -> FakeDialog | None:
        return self._dialogs.get(peer_id)

    def all_dialogs(self) -> list[FakeDialog]:
        return list(self._dialogs.values())

    def clear(self) -> None:
        self._dialogs.clear()
