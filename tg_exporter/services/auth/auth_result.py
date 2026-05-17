from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .auth_step import AuthStep


@dataclass
class AuthResult:
    step: AuthStep
    error: str | None = None
    data: dict | None = None

    @classmethod
    def ok(cls) -> AuthResult:
        return cls(step=AuthStep.SUCCESS)

    @classmethod
    def code_sent(cls, phone_code_hash: str | None = None) -> AuthResult:
        data = {"phone_code_hash": phone_code_hash} if phone_code_hash else None
        return cls(step=AuthStep.CODE_SENT, data=data)

    @classmethod
    def password_required(cls) -> AuthResult:
        return cls(step=AuthStep.PASSWORD_REQUIRED)

    @classmethod
    def error(cls, msg: str) -> AuthResult:
        return cls(step=AuthStep.ERROR, error=msg)
