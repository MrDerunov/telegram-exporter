from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .auth_step import AuthStep


@dataclass
class AuthResult:
    step: AuthStep
    error: Optional[str] = None

    @classmethod
    def ok(cls) -> "AuthResult":
        return cls(step=AuthStep.SUCCESS)

    @classmethod
    def code_sent(cls) -> "AuthResult":
        return cls(step=AuthStep.CODE_SENT)

    @classmethod
    def password_required(cls) -> "AuthResult":
        return cls(step=AuthStep.PASSWORD_REQUIRED)

    @classmethod
    def error(cls, msg: str) -> "AuthResult":
        return cls(step=AuthStep.ERROR, error=msg)
