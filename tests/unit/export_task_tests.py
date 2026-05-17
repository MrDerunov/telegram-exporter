"""Tests for ExportTask, ExportProgress, AuthorFilter."""
import time

import pytest

from tg_exporter.services.export.models.author_filter import AuthorFilter
from tg_exporter.services.export.models.export_progress import ExportProgress
from tg_exporter.services.export.models.export_format import ExportStatus
from tg_exporter.services.export.models.export_task import ExportTask


class TestExportTask:

    def should_match_all_when_author_filter_is_empty(self):
        af = AuthorFilter()
        assert af.matches(123)
        assert af.matches(None)
        assert af.is_empty()

    def should_match_only_specified_ids(self):
        af = AuthorFilter.from_ids([10, 20, 30])
        assert af.matches(10)
        assert not af.matches(99)
        assert not af.is_empty()

    def should_transition_through_lifecycle(self):
        p = ExportProgress()
        assert p.status == ExportStatus.PENDING
        assert p.progress_ratio is None

        p.start()
        assert p.status == ExportStatus.RUNNING
        assert p.started_at is not None

        p.total_messages = 100
        p.processed_messages = 25
        assert round(p.progress_ratio, 2) == 0.25

        time.sleep(0.01)
        assert p.elapsed_seconds is not None
        assert p.elapsed_seconds > 0

        p.finish()
        assert p.status == ExportStatus.DONE
        assert p.finished_at is not None

    def should_set_status_to_cancelled_on_cancel(self):
        p = ExportProgress()
        p.start()
        p.cancel()
        assert p.status == ExportStatus.CANCELLED

    def should_set_status_to_error_on_fail(self):
        p = ExportProgress()
        p.start()
        p.fail("network error")
        assert p.status == ExportStatus.ERROR
        assert p.error == "network error"

    def should_cap_progress_ratio_at_1(self):
        p = ExportProgress()
        p.total_messages = 10
        p.processed_messages = 15
        assert p.progress_ratio == 1.0

    def should_calculate_eta(self):
        p = ExportProgress()
        p.start()
        p.total_messages = 100
        p.processed_messages = 50
        time.sleep(0.02)
        eta = p.eta_seconds
        assert eta is not None
        assert eta > 0

    def should_return_new_instance_with_last_id(self):
        task = ExportTask(chat_id=1, chat_name="Test", output_path="/tmp")
        task2 = task.with_last_id(500)
        assert task.last_exported_id is None
        assert task2.last_exported_id == 500

    def should_detect_incremental_with_offset(self):
        t1 = ExportTask(chat_id=1, chat_name="C", output_path="/tmp", incremental=True)
        assert not t1.is_incremental_with_offset

        t2 = t1.with_last_id(100)
        assert t2.is_incremental_with_offset
