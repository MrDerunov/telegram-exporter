"""Tests for CancellationToken."""
import threading
import time
import unittest

from tg_exporter.utils.cancellation import CancellationToken, CancelledError


class TestCancellationToken(unittest.TestCase):

    def should_not_be_cancelled_by_default(self):
        t = CancellationToken()
        self.assertFalse(t.is_cancelled)

    def should_set_flag_on_cancel(self):
        t = CancellationToken()
        t.cancel()
        self.assertTrue(t.is_cancelled)

    def should_raise_when_cancelled(self):
        t = CancellationToken()
        t.cancel()
        with self.assertRaises(CancelledError):
            t.raise_if_cancelled()

    def should_not_raise_when_active(self):
        t = CancellationToken()
        t.raise_if_cancelled()  # no raise

    def should_be_idempotent_on_cancel(self):
        t = CancellationToken()
        t.cancel()
        t.cancel()  # no raise, no error
        self.assertTrue(t.is_cancelled)

    def should_clear_flag_on_reset(self):
        t = CancellationToken()
        t.cancel()
        t.reset()
        self.assertFalse(t.is_cancelled)
        t.raise_if_cancelled()  # should not raise

    def should_propagate_cancel_to_main_thread(self):
        """Cancel from another thread should be visible in main thread."""
        t = CancellationToken()

        def canceller():
            time.sleep(0.01)
            t.cancel()

        th = threading.Thread(target=canceller)
        th.start()
        th.join(timeout=1.0)
        self.assertTrue(t.is_cancelled)

    def should_return_true_when_cancelled_on_wait(self):
        t = CancellationToken()
        t.cancel()
        result = t.wait_for_cancel(timeout=0.1)
        self.assertTrue(result)

    def should_return_false_on_timeout(self):
        t = CancellationToken()
        result = t.wait_for_cancel(timeout=0.01)
        self.assertFalse(result)
