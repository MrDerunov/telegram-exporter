"""
AuthService — stateless сервис аутентификации в Telegram.

Все методы принимают необходимые параметры, не хранят состояние между вызовами.
Для операций, требующих состояния (send_code → verify_code) создаёт AuthSession внутри.
"""
from __future__ import annotations

from pathlib import Path

from tg_exporter.services.telegram.telegram_client_manager_interface import ITelegramClientManager
from tg_exporter.utils.file_utils import secure_permissions
from .auth_session import AuthSession
from .auth_result import AuthResult
from .auth_models import SendCodeParams, VerifyCodeParams, ExportSessionParams


class AuthService:
    """Stateless сервис аутентификации."""

    def __init__(self, manager: ITelegramClientManager) -> None:
        self._manager = manager

    # ------------------------------------------------------------------
    # Операции
    # ------------------------------------------------------------------

    async def check_session(self) -> AuthResult:
        """Проверяет текущую сессию. Возвращает SUCCESS если авторизован."""
        session = AuthSession(self._manager)
        return await session.check_session()

    async def send_code(self, params: SendCodeParams) -> AuthResult:
        """Отправляет код подтверждения на номер телефона."""
        session = AuthSession(self._manager)
        return await session.send_code(params.phone)

    async def verify_code(self, params: VerifyCodeParams) -> AuthResult:
        """Верифицирует код подтверждения."""
        session = AuthSession(self._manager)
        session._phone_number = params.phone
        session._phone_hash = params.phone_hash
        return await session.verify_code(params.code, params.password)

    async def verify_password(self, password: str) -> AuthResult:
        """Верифицирует пароль 2FA."""
        session = AuthSession(self._manager)
        return await session.verify_password(password)

    async def logout(self) -> None:
        """Выходит из аккаунта и уничтожает клиент."""
        session = AuthSession(self._manager)
        await session.logout()

    # ------------------------------------------------------------------
    # Утилиты
    # ------------------------------------------------------------------

    @staticmethod
    def export_session(params: ExportSessionParams) -> None:
        """Экспортирует сессию в .env файл для CI/CD."""
        content = (
            f"TG_EXPORTER_API_ID={params.api_id}\n"
            f"TG_EXPORTER_API_HASH={params.api_hash}\n"
            f"TG_EXPORTER_SESSION={params.session_string}\n"
        )
        params.output_path.write_text(content)
        secure_permissions(params.output_path)
