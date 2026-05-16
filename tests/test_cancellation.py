"""Tests for CancellationToken."""
import threading
import time
import unittest

from tg_exporter.utils.cancellation import CancellationToken, CancelledError


class TestCancellationToken(unittest.TestCase):

    def test_not_cancelled_by_default(self):
        t = CancellationToken()
        self.assertFalse(t.is_cancelled)

    def test_cancel_sets_flag(self):
        t = CancellationToken()
        t.cancel()
        self.assertTrue(t.is_cancelled)

    def test_raise_if_cancelled_raises(self):
        t = CancellationToken()
        t.cancel()
        with self.assertRaises(CancelledError):
            t.raise_if_cancelled()

    def test_raise_if_cancelled_no_raise_when_active(self):
        t = CancellationToken()
        t.raise_if_cancelled()  # no raise

    def test_cancel_is_idempotent(self):
        t = CancellationToken()
        t.cancel()
        t.cancel()  # no raise, no error
        self.assertTrue(t.is_cancelled)

    def test_reset_clears_flag(self):
        t = CancellationToken()
        t.cancel()
        t.reset()
        self.assertFalse(t.is_cancelled)
        t.raise_if_cancelled()  # should not raise

    def test_thread_safety(self):
        """Cancel from another thread should be visible in main thread."""
        t = CancellationToken()

        def canceller():
            time.sleep(0.01)
            t.cancel()

        th = threading.Thread(target=canceller)
        th.start()
        th.join(timeout=1.0)
        self.assertTrue(t.is_cancelled)

    def test_wait_for_cancel_returns_true_when_cancelled(self):
        t = CancellationToken()
        t.cancel()
        result = t.wait_for_cancel(timeout=0.1)
        self.assertTrue(result)

    def test_wait_for_cancel_returns_false_on_timeout(self):
        t = CancellationToken()
        result = t.wait_for_cancel(timeout=0.01)
        self.assertFalse(result)
