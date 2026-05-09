"""Тесты абстрактного SecretProvider."""
from __future__ import annotations

import pytest

from tg_exporter.secrets.secret_provider import SecretProvider


class TestSecretProviderABC:
    def test_cannot_instantiate_abstract(self):
        """SecretProvider — абстрактный класс, нельзя создать напрямую."""
        with pytest.raises(TypeError):
            SecretProvider()  # type: ignore[abstract]

    def test_writable_default_is_false(self):
        """По умолчанию writable = False."""
        assert SecretProvider.writable is False
