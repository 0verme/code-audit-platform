import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import audit.engine as audit_engine  # noqa: E402
from audit.run_failure_result import (  # noqa: E402
    SVN_CLI_MISSING_HINT,
    build_engine_load_failure_result,
    build_failure_result,
)
from audit.checks.svn_service import SvnCliNotFoundError  # noqa: E402


class RunFailureResultTests(unittest.TestCase):
    def setUp(self):
        self.previous_mods = audit_engine._mods

    def tearDown(self):
        audit_engine._mods = self.previous_mods

    def _new_run(self, *, source_type="svn"):
        run = audit_engine.TaskRun.__new__(audit_engine.TaskRun)
        run.task_id = 1
        run.repo = "svn://example.com/repos/branches/hcyt/demo"
        run.workflow = "hcyt"
        run.source_type = source_type
        run.logs = []
        run.log = lambda msg, level="INFO": run.logs.append(
            {"level": level, "msg": str(msg)}
        )
        run.update = lambda *args, **kwargs: None
        run.task_running = lambda *args, **kwargs: None
        run.task_success = lambda *args, **kwargs: None
        run.run_hcyt = Mock(return_value={"task": {"status": "pass"}})
        run.run_nups = Mock()
        run.run_fine = Mock()
        run.finished = []
        run.finish = lambda status, report=None, error=None: run.finished.append(
            {"status": status, "report": report, "error": error}
        )
        return run

    def test_build_failure_result_adds_svn_cli_hint_only_for_command_start_failure(self):
        result = build_failure_result(SvnCliNotFoundError("svn missing"), source_type="svn")

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["error"], "svn missing" + SVN_CLI_MISSING_HINT)

    def test_build_failure_result_does_not_add_svn_hint_for_local_source(self):
        result = build_failure_result(SvnCliNotFoundError("svn missing"), source_type="local")

        self.assertEqual(result, {"status": "fail", "error": "svn missing"})

    def test_build_failure_result_does_not_misclassify_missing_svn_config(self):
        missing_config = FileNotFoundError("SVN 配置文件不存在: /opt/code-audit-platform/backend/configs/svn.yaml")

        result = build_failure_result(missing_config, source_type="svn")

        self.assertEqual(result, {"status": "fail", "error": str(missing_config)})

    def test_engine_load_failure_result_keeps_error_payload_text(self):
        result = build_engine_load_failure_result("import traceback")

        self.assertEqual(
            result,
            {"status": "fail", "error": "真实审查引擎加载失败。\nimport traceback"},
        )

    def test_source_load_failure_keeps_outer_failure_result_structure(self):
        audit_engine._mods = types.SimpleNamespace(
            svn_main=Mock(side_effect=SvnCliNotFoundError("svn missing"))
        )
        run = self._new_run(source_type="svn")

        with patch.object(audit_engine, "_load_real_modules", lambda: None):
            run.run()

        self.assertEqual(len(run.finished), 1)
        self.assertEqual(run.finished[0]["status"], "fail")
        self.assertIsNone(run.finished[0]["report"])
        self.assertEqual(run.finished[0]["error"], "svn missing" + SVN_CLI_MISSING_HINT)
        self.assertTrue(
            any(
                log["level"] == "ERR"
                and log["msg"] == "任务异常: svn missing" + SVN_CLI_MISSING_HINT
                for log in run.logs
            )
        )

    def test_workflow_exception_keeps_outer_failure_result_structure(self):
        audit_engine._mods = types.SimpleNamespace(
            svn_main=lambda *_args: {
                "create_revision": "123",
                "exported_paths": ["demo.sql"],
            }
        )
        run = self._new_run(source_type="svn")

        with patch.object(audit_engine, "_load_real_modules", lambda: None):
            with patch.object(audit_engine, "run_workflow", side_effect=RuntimeError("workflow boom")):
                run.run()

        self.assertEqual(len(run.finished), 1)
        self.assertEqual(run.finished[0], {"status": "fail", "report": None, "error": "workflow boom"})
        self.assertTrue(
            any(
                log["level"] == "ERR" and log["msg"] == "任务异常: workflow boom"
                for log in run.logs
            )
        )


if __name__ == "__main__":
    unittest.main()
