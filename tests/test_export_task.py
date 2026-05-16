"""Tests for ExportTask, ExportProgress, AuthorFilter."""
import time
import unittest

from tg_exporter.services.export.models.author_filter import AuthorFilter
from tg_exporter.services.export.models.export_progress import ExportProgress
from tg_exporter.services.export.models.export_format import ExportStatus
from tg_exporter.services.export.models.export_task import ExportTask


class TestExportTask(unittest.TestCase):

    def test_author_filter_empty_matches_all(self):
        af = AuthorFilter()
        self.assertTrue(af.matches(123))
        self.assertTrue(af.matches(None))
        self.assertTrue(af.is_empty())

    def test_author_filter_with_ids(self):
        af = AuthorFilter.from_ids([10, 20, 30])
        self.assertTrue(af.matches(10))
        self.assertFalse(af.matches(99))
        self.assertFalse(af.is_empty())

    def test_export_progress_lifecycle(self):
        p = ExportProgress()
        self.assertEqual(p.status, ExportStatus.PENDING)
        self.assertIsNone(p.progress_ratio)

        p.start()
        self.assertEqual(p.status, ExportStatus.RUNNING)
        self.assertIsNotNone(p.started_at)

        p.total_messages = 100
        p.processed_messages = 25
        self.assertAlmostEqual(p.progress_ratio, 0.25)

        time.sleep(0.01)
        self.assertIsNotNone(p.elapsed_seconds)
        self.assertGreater(p.elapsed_seconds, 0)

        p.finish()
        self.assertEqual(p.status, ExportStatus.DONE)
        self.assertIsNotNone(p.finished_at)

    def test_export_progress_cancel(self):
        p = ExportProgress()
        p.start()
        p.cancel()
        self.assertEqual(p.status, ExportStatus.CANCELLED)

    def test_export_progress_fail(self):
        p = ExportProgress()
        p.start()
        p.fail("network error")
        self.assertEqual(p.status, ExportStatus.ERROR)
        self.assertEqual(p.error, "network error")

    def test_export_progress_ratio_capped_at_1(self):
        p = ExportProgress()
        p.total_messages = 10
        p.processed_messages = 15  # больше total
        self.assertEqual(p.progress_ratio, 1.0)

    def test_export_progress_eta(self):
        p = ExportProgress()
        p.start()
        p.total_messages = 100
        p.processed_messages = 50
        time.sleep(0.02)
        eta = p.eta_seconds
        self.assertIsNotNone(eta)
        self.assertGreater(eta, 0)

    def test_export_task_immutable(self):
        task = ExportTask(chat_id=1, chat_name="Test", output_path="/tmp")
        task2 = task.with_last_id(500)
        self.assertIsNone(task.last_exported_id)
        self.assertEqual(task2.last_exported_id, 500)

    def test_export_task_incremental_flag(self):
        t1 = ExportTask(chat_id=1, chat_name="C", output_path="/tmp", incremental=True)
        self.assertFalse(t1.is_incremental_with_offset)  # нет last_id

        t2 = t1.with_last_id(100)
        self.assertTrue(t2.is_incremental_with_offset)
