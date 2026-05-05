from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class AuthStep(Enum):
    CODE_SENT = auto()          # код отправлен
    PASSWORD_REQUIRED = auto()  # нужен пароль 2FA
    SUCCESS = auto()            # авторизован
    ERROR = auto()


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
