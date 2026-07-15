import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.modules.audit.engine as audit_engine  # noqa: E402


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
            self.assertIs(context.runtime_context.source_payload, svn_result)
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

    def test_run_hcyt_keeps_extracted_orchestration_order(self):
        class InputFiles:
            def as_run_inputs(self):
                grouped = {
                    "dws": [],
                    "hive": [],
                    "python": [],
                    "sbin": [],
                    "config": [],
                    "recv": [],
                }
                return (
                    None,
                    None,
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    None,
                    None,
                    None,
                    None,
                    None,
                    grouped,
                    [{"path": "demo.sql"}],
                    [],
                )

        run = audit_engine.TaskRun.__new__(audit_engine.TaskRun)
        run.task_id = 7
        run.repo = "svn://repo/hcyt/demo"
        run.workflow = "hcyt"
        run.ai_enabled = False
        run.debug_enabled = False
        run.author = "tester"
        run.source_type = "svn"
        run.logs = []
        run.start_ts = 0
        run.task_running = lambda *args, **kwargs: None
        run.task_success = lambda *args, **kwargs: None
        run.task_skipped = lambda *args, **kwargs: None
        run.update = lambda *args, **kwargs: None
        run.set_partial = lambda *args, **kwargs: None
        run.save_category_rows = lambda *args, **kwargs: None

        audit_engine._mods = types.SimpleNamespace(
            re_service=types.SimpleNamespace(),
            hcyt=types.SimpleNamespace(),
        )
        calls = []

        def fake_collect_hcyt_input_files(**kwargs):
            calls.append("collect_hcyt_input_files")
            self.assertEqual(kwargs["svn_result"]["exported_paths"], ["demo.sql"])
            return InputFiles()

        def fake_build_source_classified_progress(**kwargs):
            calls.append("build_source_classified_progress")
            return {"changes": kwargs["changes"], "conflicts": kwargs["conflicts"]}

        def fake_publish_hcyt_progress(set_partial, payload):
            calls.append("publish_hcyt_progress")
            self.assertEqual(payload, {"changes": [{"path": "demo.sql"}], "conflicts": []})

        def fake_run_hcyt_inspections(**kwargs):
            calls.append("run_hcyt_inspections")
            return types.SimpleNamespace(
                schedule={"rows": []},
                py_scripts=[],
                ref_tables=[],
                deps=[],
                asset_issues=[],
                unified_asset_issues=[],
                lineage_summary={"resultTables": [], "jobs": [], "warnings": []},
            )

        def fake_run_hcyt_ai_review(**kwargs):
            calls.append("run_hcyt_ai_review")
            self.assertFalse(kwargs["ai_enabled"])
            return None

        def fake_build_hcyt_report(**kwargs):
            calls.append("build_hcyt_report")
            self.assertEqual(kwargs["changes"], [{"path": "demo.sql"}])
            self.assertEqual(kwargs["conflicts"], [])
            return {"task": {"status": "pass"}}

        svn_result = {
            "exported_paths": ["demo.sql"],
            "branch_changed_files": ["demo.sql"],
            "trunk_conflict_files": [],
            "create_revision": "123",
            "source_type": "svn",
        }

        with patch.object(audit_engine, "collect_hcyt_input_files", side_effect=fake_collect_hcyt_input_files):
            with patch.object(
                audit_engine,
                "build_source_classified_progress",
                side_effect=fake_build_source_classified_progress,
            ):
                with patch.object(audit_engine, "publish_hcyt_progress", side_effect=fake_publish_hcyt_progress):
                    with patch.object(audit_engine, "run_hcyt_inspections", side_effect=fake_run_hcyt_inspections):
                        with patch.object(audit_engine, "run_hcyt_ai_review", side_effect=fake_run_hcyt_ai_review):
                            with patch.object(audit_engine, "build_hcyt_report", side_effect=fake_build_hcyt_report):
                                report = run.run_hcyt(svn_result)

        self.assertEqual(report, {"task": {"status": "pass"}})
        self.assertEqual(
            calls,
            [
                "collect_hcyt_input_files",
                "build_source_classified_progress",
                "publish_hcyt_progress",
                "run_hcyt_inspections",
                "run_hcyt_ai_review",
                "build_hcyt_report",
            ],
        )


if __name__ == "__main__":
    unittest.main()
