import unittest
from datetime import datetime, timedelta

from app.modules.audit.run import AuditRunState, AuditTask, AuditTaskStatus


class AuditRunModelTest(unittest.TestCase):
    def test_task_requires_valid_identity_and_weight(self):
        with self.assertRaises(ValueError):
            AuditTask("", "DWS SQL")
        with self.assertRaises(ValueError):
            AuditTask("dws", "")
        with self.assertRaises(ValueError):
            AuditTask("dws", "DWS SQL", weight=0)

    def test_task_state_records_status_duration_error_and_summary(self):
        run = AuditRunState(run_id=7, workflow="hcyt")
        state = run.add_task(AuditTask("dws", "DWS SQL", weight=2))
        started_at = datetime(2026, 1, 1, 10, 0, 0)
        finished_at = started_at + timedelta(milliseconds=250)

        state.mark_running(now=started_at)
        state.mark_success(
            result={"rows": [{"level": "warn"}]},
            summary={"warnings": 1},
            now=finished_at,
        )

        self.assertEqual(state.status, AuditTaskStatus.SUCCESS)
        self.assertEqual(state.duration_ms, 250)
        self.assertIsNone(state.error)
        payload = state.to_dict(include_result=True)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["summary"], {"warnings": 1})
        self.assertEqual(payload["result"], {"rows": [{"level": "warn"}]})
        self.assertEqual(payload["errorMessage"], None)

    def test_failed_and_skipped_tasks_are_terminal_without_blocking_dependents(self):
        run = AuditRunState(run_id="run-1", workflow="hcyt")
        run.add_task(AuditTask("schedule", "调度表检查"))
        dependent = run.add_task(AuditTask("lineage", "依赖链分析", dependencies=("schedule",)))

        self.assertEqual(run.ready_tasks()[0].task.key, "schedule")
        self.assertNotIn(dependent, run.ready_tasks())

        run.get_task("schedule").mark_failed("Excel shape mismatch")
        self.assertTrue(run.get_task("schedule").is_terminal)
        self.assertIn(dependent, run.ready_tasks())

        dependent.mark_skipped("metadata unavailable")
        self.assertTrue(dependent.is_terminal)
        self.assertEqual(dependent.to_dict()["status"], "skipped")
        self.assertEqual(dependent.to_dict()["error"], "metadata unavailable")
        self.assertEqual(dependent.to_dict()["errorMessage"], "metadata unavailable")

    def test_weighted_progress_uses_terminal_tasks(self):
        run = AuditRunState(run_id=8, workflow="hcyt")
        run.add_task(AuditTask("prefetch", "前置任务", weight=1))
        run.add_task(AuditTask("dws", "DWS SQL", weight=3))
        run.add_task(AuditTask("hive", "Hive SQL", weight=2))

        run.get_task("prefetch").mark_success()
        run.get_task("dws").mark_running()

        self.assertEqual(run.progress["total"], 3)
        self.assertEqual(run.progress["completed"], 1)
        self.assertEqual(run.progress["failed"], 0)
        self.assertEqual(run.progress["skipped"], 0)
        self.assertEqual(run.progress["totalWeight"], 6)
        self.assertEqual(run.progress["completedWeight"], 1)
        self.assertEqual(run.progress["percent"], 16)
        self.assertEqual(run.progress["running"], ["dws"])

    def test_run_serializes_partial_report_tasks_and_logs(self):
        run = AuditRunState(run_id=9, workflow="hcyt")
        run.add_task(AuditTask("changes", "变更文件"))
        run.mark_running()
        run.set_section("changes", [{"path": "demo.sql"}])
        run.add_log("changes ready", level="INFO", now=datetime(2026, 1, 1, 10, 0, 0))
        run.get_task("changes").mark_success(summary={"files": 1})
        run.mark_finished()

        payload = run.to_dict()
        self.assertEqual(payload["runId"], 9)
        self.assertEqual(payload["status"], "success")
        self.assertIsNotNone(payload["durationMs"])
        self.assertIsNone(payload["errorMessage"])
        self.assertEqual(payload["partialReport"], {"changes": [{"path": "demo.sql"}]})
        self.assertEqual(payload["tasks"]["changes"]["summary"], {"files": 1})
        self.assertEqual(payload["logs"][0]["msg"], "changes ready")


if __name__ == "__main__":
    unittest.main()
