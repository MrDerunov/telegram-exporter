from __future__ import annotations

from enum import Enum, auto


class AuthStep(Enum):
    CODE_SENT = auto()          # код отправлен
    PASSWORD_REQUIRED = auto()  # нужен пароль 2FA
    SUCCESS = auto()            # авторизован
    ERROR = auto()
