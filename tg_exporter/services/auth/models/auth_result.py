from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .auth_step import AuthStep


@dataclass
class AuthResult:
    step: AuthStep
    error: str | None = None

    @classmethod
    def ok(cls) -> AuthResult:
        return cls(step=AuthStep.SUCCESS)

    @classmethod
    def password_required(cls) -> AuthResult:
        return cls(step=AuthStep.PASSWORD_REQUIRED)

    @classmethod
    def error(cls, msg: str) -> AuthResult:
        return cls(step=AuthStep.ERROR, error=msg)


@dataclass
class SendCodeResult(AuthResult):
    """Результат send_code. Наследует step/error от AuthResult, добавляет phone_code_hash."""
    phone_code_hash: str = ""

    @classmethod
    def ok(cls, phone_code_hash: str) -> SendCodeResult:
        return cls(step=AuthStep.CODE_SENT, phone_code_hash=phone_code_hash)

    @classmethod
    def error(cls, msg: str) -> SendCodeResult:
        return cls(step=AuthStep.ERROR, error=msg, phone_code_hash="")
