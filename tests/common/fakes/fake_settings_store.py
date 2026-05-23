"""In-memory ISettingsStore для тестов."""
from __future__ import annotations
from tg_exporter.settings.configs import ISettingsStore, StateModel


class FakeSettingsStore(ISettingsStore):
    def __init__(self) -> None:
        self._state = StateModel()

    def load(self) -> StateModel:
        return self._state

    def save(self, state: StateModel) -> None:
        self._state = state
