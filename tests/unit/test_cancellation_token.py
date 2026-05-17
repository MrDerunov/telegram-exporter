"""Tests for CancellationToken."""
import threading
import time

import pytest

from tg_exporter.utils.cancellation import CancellationToken, CancelledError


class TestCancellationToken:
    def test_not_be_cancelled_by_default(self):
        t = CancellationToken()
        assert not t.is_cancelled

    def test_set_flag_on_cancel(self):
        t = CancellationToken()
        t.cancel()
        assert t.is_cancelled

    def test_raise_when_cancelled(self):
        t = CancellationToken()
        t.cancel()
        with pytest.raises(CancelledError):
            t.raise_if_cancelled()

    def test_not_raise_when_active(self):
        t = CancellationToken()
        t.raise_if_cancelled()

    def test_be_idempotent_on_cancel(self):
        t = CancellationToken()
        t.cancel()
        t.cancel()
        assert t.is_cancelled

    def test_return_true_when_cancelled_on_wait(self):
        t = CancellationToken()
        t.cancel()
        result = t.wait_for_cancel(timeout=0.1)
        assert result is True

    def test_return_false_on_timeout(self):
        t = CancellationToken()
        result = t.wait_for_cancel(timeout=0.01)
        assert result is False
