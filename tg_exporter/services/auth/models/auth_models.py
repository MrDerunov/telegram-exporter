"""Типы параметров для операций AuthService."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SendCodeParams:
    """Параметры для отправки кода подтверждения."""
    phone: str


@dataclass(frozen=True)
class VerifyCodeParams:
    """Параметры для верификации кода."""
    phone: str
    phone_hash: str
    code: str
    password: str = ""


@dataclass(frozen=True)
class ExportSessionParams:
    """Параметры для экспорта сессии в .env файл."""
    api_id: str
    api_hash: str
    session_string: str
    output_path: Path
