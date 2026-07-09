import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import audit.engine as audit_engine  # noqa: E402


class EngineOrchestrationContractTests(unittest.TestCase):
    def setUp(self):
        self.previous_mods = audit_engine._mods

    def tearDown(self):
        audit_engine._mods = self.previous_mods

    def _new_run(self):
        run = audit_engine.TaskRun.__new__(audit_engine.TaskRun)
        run.task_id = 1
        run.repo = "svn://example.com/repos/branches/hcyt/demo"
        run.workflow = "hcyt"
        run.source_type = "svn"
        run.logs = []
        run.log = lambda msg, level="INFO": run.logs.append(
            {"level": level, "msg": str(msg)}
        )
        run.update = lambda *args, **kwargs: None
        run.task_running = lambda *args, **kwargs: None
        run.task_success = lambda *args, **kwargs: None
        run.run_hcyt = lambda _svn_result: {"task": {"status": "pass"}}
        run.run_nups = lambda _svn_result: {"task": {"status": "pass"}}
        run.run_fine = lambda _svn_result: {"task": {"status": "pass"}}
        run.finished = []
        run.finish = lambda status, report=None, error=None: run.finished.append(
            {"status": status, "report": report, "error": error}
        )
        return run

    def test_detect_workflow_remains_exported_from_engine_for_api_layer(self):
        self.assertEqual(
            audit_engine.detect_workflow("svn://repo/branches/fine-report/demo", "hcyt"),
            "fine-report",
        )

    def test_task_run_keeps_source_workflow_finalizer_order(self):
        audit_engine._mods = types.SimpleNamespace()
        run = self._new_run()
        calls = []
        svn_result = {
            "create_revision": "123",
            "exported_paths": ["demo.sql"],
            "source_type": "svn",
        }

        def fake_resolve_workspace(*args, **kwargs):
            calls.append(("resolve_workspace", args, kwargs))
            return svn_result

        def fake_run_workflow(context):
            calls.append(("run_workflow", context))
            self.assertEqual(context.workflow, "hcyt")
            self.assertIs(context.svn_result, svn_result)
            return {"task": {"status": "pass"}, "body": "workflow"}

        def fake_finalize_run_result(workflow_result, **kwargs):
            calls.append(("finalize_run_result", workflow_result, kwargs))
            self.assertEqual(workflow_result, {"task": {"status": "pass"}, "body": "workflow"})
            self.assertIs(kwargs["svn_result"], svn_result)
            self.assertEqual(kwargs["source_ref"], run.repo)
            self.assertEqual(kwargs["fallback_source_type"], "svn")
            return {
                "task": {"status": "pass"},
                "body": "workflow",
                "sourceType": "svn",
                "logs": kwargs["logs"],
            }

        with patch.object(audit_engine, "_load_real_modules", lambda: None):
            with patch.object(audit_engine, "resolve_workspace", side_effect=fake_resolve_workspace):
                with patch.object(audit_engine, "run_workflow", side_effect=fake_run_workflow):
                    with patch.object(
                        audit_engine,
                        "finalize_run_result",
                        side_effect=fake_finalize_run_result,
                    ):
                        run.run()

        self.assertEqual(
            [call[0] for call in calls],
            ["resolve_workspace", "run_workflow", "finalize_run_result"],
        )
        self.assertEqual(len(run.finished), 1)
        self.assertEqual(run.finished[0]["status"], "pass")
        self.assertEqual(run.finished[0]["report"]["sourceType"], "svn")
        self.assertIsNone(run.finished[0]["error"])


if __name__ == "__main__":
    unittest.main()
