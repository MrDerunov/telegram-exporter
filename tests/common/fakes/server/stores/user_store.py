"""Хранилище фейковых пользователей."""

from __future__ import annotations

from common.fakes.server.data_objects.fake_user import FakeUser


class UserStore:
    def __init__(self) -> None:
        self._users: dict[int, FakeUser] = {}

    def add_user(self, user: FakeUser) -> None:
        self._users[user.id] = user

    def get_user(self, user_id: int) -> FakeUser | None:
        return self._users.get(user_id)

    def all_users(self) -> list[FakeUser]:
        return list(self._users.values())

    def clear(self) -> None:
        self._users.clear()
