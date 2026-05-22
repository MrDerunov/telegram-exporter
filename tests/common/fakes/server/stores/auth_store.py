"""Хранилище состояния авторизации."""

from __future__ import annotations


class AuthStore:
    def __init__(self) -> None:
        self._authorized: bool = False
        self._code_requests: dict[str, str] = {}
        self._session_str: str = ""
        self._signed_in_user_id: int | None = None

    def set_authorized(self, authorized: bool) -> None:
        self._authorized = authorized

    def is_authorized(self) -> bool:
        return self._authorized

    def add_code_request(self, phone: str, code_hash: str) -> None:
        self._code_requests[phone] = code_hash

    def get_code_hash(self, phone: str) -> str | None:
        return self._code_requests.get(phone)

    def set_session(self, session_str: str) -> None:
        self._session_str = session_str

    def get_session(self) -> str:
        return self._session_str

    def set_user_id(self, user_id: int | None) -> None:
        self._signed_in_user_id = user_id

    def get_user_id(self) -> int | None:
        return self._signed_in_user_id

    def clear(self) -> None:
        self._authorized = False
        self._code_requests.clear()
        self._session_str = ""
        self._signed_in_user_id = None
