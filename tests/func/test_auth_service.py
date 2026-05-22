"""Тесты AuthService — stateless сервис аутентификации."""

from __future__ import annotations

import pytest

from tg_exporter.services.auth.models.auth_result import AuthResult, SendCodeResult
from tg_exporter.services.auth.models.auth_models import SendCodeParams, VerifyCodeParams, ExportSessionParams
from tg_exporter.services.auth.models.auth_step import AuthStep
from tg_exporter.services.telegram import AuthService
from tests.common.fakes import FakeTelegramClient, FakeTelegramClientManager


class TestAuthService:

    @pytest.fixture(autouse=True)
    def _setup(self):
        self._fake_client = FakeTelegramClient()
        self._manager = FakeTelegramClientManager(self._fake_client)
        self.auth = AuthService(self._manager)

    # ------------------------------------------------------------------
    # check_session
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_check_session_returns_success_when_authorized(self):
        """Авторизованный клиент — SUCCESS."""
        self._fake_client.server.auth.set_authorized(True)
        result = await self.auth.check_session()
        assert result.step == AuthStep.SUCCESS

    @pytest.mark.asyncio
    async def test_check_session_returns_error_when_not_authorized(self):
        """Неавторизованный клиент — ошибка."""
        self._fake_client.server.auth.set_authorized(False)
        result = await self.auth.check_session()
        assert result.step == AuthStep.ERROR

    # ------------------------------------------------------------------
    # send_code
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_code_returns_send_code_result(self):
        """send_code возвращает SendCodeResult с phone_code_hash."""
        result = await self.auth.send_code(SendCodeParams(phone="+7999"))
        assert isinstance(result, SendCodeResult)
        assert result.step == AuthStep.CODE_SENT

    @pytest.mark.asyncio
    async def test_send_code_returns_success_when_already_authorized(self):
        """Уже авторизован — SUCCESS."""
        self._fake_client.server.auth.set_authorized(True)
        result = await self.auth.send_code(SendCodeParams(phone="+7999"))
        assert result.step == AuthStep.SUCCESS

    @pytest.mark.asyncio
    async def test_send_code_returns_error_for_empty_phone(self):
        """Пустой телефон — ошибка."""
        result = await self.auth.send_code(SendCodeParams(phone=""))
        assert result.step == AuthStep.ERROR
        assert result.error is not None

    # ------------------------------------------------------------------
    # verify_code
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_code_returns_success_for_valid_code(self):
        """Валидный код — SUCCESS."""
        result = await self.auth.verify_code(VerifyCodeParams(
            phone="+7999",
            phone_hash="fake_hash",
            code="12345",
        ))
        assert result.step == AuthStep.SUCCESS

    @pytest.mark.asyncio
    async def test_verify_code_returns_error_for_empty_code(self):
        """Пустой код — ошибка."""
        result = await self.auth.verify_code(VerifyCodeParams(
            phone="+7999",
            phone_hash="fake_hash",
            code="",
        ))
        assert result.step == AuthStep.ERROR

    # ------------------------------------------------------------------
    # verify_password
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_password_returns_success(self):
        """Валидный пароль 2FA — SUCCESS."""
        result = await self.auth.verify_password("secret")
        assert result.step == AuthStep.SUCCESS

    @pytest.mark.asyncio
    async def test_verify_password_returns_error_for_empty_password(self):
        """Пустой пароль 2FA — ошибка."""
        result = await self.auth.verify_password("")
        assert result.step == AuthStep.ERROR

    # ------------------------------------------------------------------
    # export_session
    # ------------------------------------------------------------------

    def test_export_session_writes_env_file(self, tmp_path):
        """export_session создаёт .env файл с правильным содержимым."""
        output = tmp_path / "secrets.env"
        self.auth.export_session(ExportSessionParams(
            api_id="123",
            api_hash="abc",
            session_string="sess_xyz",
            output_path=output,
        ))
        assert output.exists()
        content = output.read_text()
        assert "TG_EXPORTER_API_ID=123" in content
        assert "TG_EXPORTER_API_HASH=abc" in content
        assert "TG_EXPORTER_SESSION=sess_xyz" in content
