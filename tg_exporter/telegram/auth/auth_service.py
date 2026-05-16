"""
AuthService — логика аутентификации в Telegram.

Полностью отделён от UI. Принимает callback для уведомлений о результате.
Все методы выполняются в фоновом потоке (там где живёт TelegramClient).
"""

from __future__ import annotations

from typing import Optional

from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PhoneNumberInvalidError,
    PhoneNumberBannedError,
    PhoneNumberFloodError,
    PasswordHashInvalidError,
    FloodWaitError,
    ApiIdInvalidError,
    AuthKeyInvalidError,
    AuthKeyUnregisteredError,
    SendCodeUnavailableError,
)

from ..telegram_client_manager_interface import ITelegramClientManager
from ...utils.logger import logger
from .auth_result import AuthResult
from .auth_step import AuthStep


class AuthService:
    """
    Оркестратор процесса входа в Telegram.

    Состояние сессии (phone_hash, phone_number) хранится здесь,
    не в App и не в UI.
    """

    def __init__(self, manager: ITelegramClientManager) -> None:
        self._manager = manager
        self._phone_number: str | None = None
        self._phone_hash: str | None = None

    # ---- Public API ----

    async def check_session(self) -> AuthResult:
        """
        Проверяет текущую сессию. Если авторизован — сохраняет и возвращает SUCCESS.
        Вызывать при старте приложения.
        """
        try:
            client = self._manager.create_client()
            await client.connect()
            if await client.is_authorized():
                await self._manager.save_session()
                return AuthResult.ok()
            return AuthResult.error("Требуется вход")
        except (AuthKeyInvalidError, AuthKeyUnregisteredError):
            return AuthResult.error("Сессия устарела. Войдите заново.")
        except ApiIdInvalidError:
            return AuthResult.error("Неверный API ID или API Hash. Проверьте настройки.")
        except Exception as exc:
            logger.error("check_session failed", exc=exc)
            return AuthResult.error(_friendly(exc))

    async def send_code(self, phone: str) -> AuthResult:
        """
        Отправляет код подтверждения на номер телефона.
        Запоминает phone_hash для последующего verify_code().
        """
        phone = (phone or "").strip()
        if not phone:
            return AuthResult.error("Введите номер телефона.")
        try:
            client = self._manager.create_client()
            await client.connect()
            if await client.is_authorized():
                await self._manager.save_session()
                return AuthResult.ok()
            sent = await client.send_code_request(phone)
            self._phone_number = phone
            self._phone_hash = sent.phone_code_hash
            return AuthResult.code_sent()
        except PhoneNumberInvalidError:
            return AuthResult.error("Неверный номер телефона.")
        except PhoneNumberBannedError:
            return AuthResult.error("Этот номер заблокирован в Telegram.")
        except PhoneNumberFloodError:
            return AuthResult.error("Слишком много попыток. Попробуйте позже.")
        except SendCodeUnavailableError:
            return AuthResult.error("Не удалось отправить код. Попробуйте другой способ.")
        except FloodWaitError as exc:
            return AuthResult.error(f"Слишком много запросов. Подождите {exc.seconds} сек.")
        except ApiIdInvalidError:
            return AuthResult.error("Неверный API ID или API Hash. Проверьте настройки.")
        except Exception as exc:
            logger.error("send_code failed", exc=exc)
            return AuthResult.error(_friendly(exc))

    async def verify_code(self, code: str, password: str = "") -> AuthResult:
        """
        Верифицирует код из Telegram.
        Если включена 2FA и код верен — автоматически пробует password.
        """
        code = (code or "").strip()
        if not code:
            return AuthResult.error("Введите код из Telegram.")
        if not self._phone_hash:
            return AuthResult.error("Сначала нажмите «Получить код».")
        phone = self._phone_number
        if not phone:
            return AuthResult.error("Введите номер телефона.")
        try:
            client = self._manager.create_client()
            await client.connect()
            await client.sign_in(phone=phone, code=code)
            self._manager.save_session()
            return AuthResult.ok()
        except SessionPasswordNeededError:
            if (password or "").strip():
                return await self.verify_password(password)
            return AuthResult.password_required()
        except PhoneCodeInvalidError:
            return AuthResult.error("Неверный код. Проверьте и попробуйте снова.")
        except PhoneCodeExpiredError:
            return AuthResult.error("Код устарел. Запросите новый код.")
        except FloodWaitError as exc:
            return AuthResult.error(f"Слишком много попыток. Подождите {exc.seconds} сек.")
        except Exception as exc:
            logger.error("verify_code failed", exc=exc)
            return AuthResult.error(_friendly(exc))

    async def verify_password(self, password: str) -> AuthResult:
        """Верифицирует пароль двухфакторной аутентификации."""
        password = (password or "").strip()
        if not password:
            return AuthResult.error("Нужен пароль 2FA.")
        try:
            client = self._manager.create_client()
            await client.connect()
            await client.sign_in_password(password)
            self._manager.save_session()
            return AuthResult.ok()
        except PasswordHashInvalidError:
            return AuthResult.error("Неверный пароль двухфакторной аутентификации.")
        except FloodWaitError as exc:
            return AuthResult.error(f"Слишком много попыток. Подождите {exc.seconds} сек.")
        except Exception as exc:
            logger.error("verify_password failed", exc=exc)
            return AuthResult.error(_friendly(exc))

    async def logout(self) -> None:
        """Выходит из аккаунта и уничтожает клиент."""
        try:
            client = self._manager.create_client()
            await client.connect()
            await client.log_out()
        except Exception:
            pass
        finally:
            await self._manager.destroy()
            self._phone_number = None
            self._phone_hash = None


# ---- Helpers ----

def _friendly(exc: Exception) -> str:
    """Переводит необработанные исключения Telethon в читаемый русский текст."""
    msg = str(exc)
    if "The password" in msg and "is invalid" in msg:
        return "Неверный пароль двухфакторной аутентификации."
    if "Two-steps verification" in msg or "PASSWORD_HASH_INVALID" in msg:
        return "Неверный пароль двухфакторной аутентификации."
    if "PHONE_CODE_INVALID" in msg:
        return "Неверный код. Проверьте и попробуйте снова."
    if "PHONE_CODE_EXPIRED" in msg:
        return "Код устарел. Запросите новый код."
    if "PHONE_NUMBER_INVALID" in msg:
        return "Неверный номер телефона."
    if "PHONE_NUMBER_BANNED" in msg:
        return "Этот номер заблокирован в Telegram."
    if "API_ID_INVALID" in msg or "api_id" in msg.lower():
        return "Неверный API ID или API Hash. Проверьте настройки."
    if "AUTH_KEY_INVALID" in msg or "AUTH_KEY_UNREGISTERED" in msg:
        return "Сессия недействительна. Войдите заново."
    if "FLOOD_WAIT" in msg:
        return "Слишком много запросов. Подождите немного."
    if "network" in msg.lower() or "connect" in msg.lower():
        return "Ошибка соединения. Проверьте интернет."
    if "ResendCodeRequest" in msg or "options for this type" in msg:
        return "Все способы отправки кода исчерпаны. Попробуйте позже."
    return msg
