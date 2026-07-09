import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from audit.compat import (  # noqa: E402
    build_audit_run_partial_result_payload,
    build_legacy_fine_audit_result_rows,
    build_legacy_nups_audit_result_rows,
    normalize_legacy_audit_result_groups,
)


class AuditCompatTests(unittest.TestCase):
    def test_partial_result_keeps_final_report_compatibility_wrapper(self):
        final_report = {"task": {"status": "pass"}, "changes": [{"path": "demo.sql"}]}
        payload = build_audit_run_partial_result_payload(
            7,
            {
                "workflow": "hcyt",
                "status": "success",
                "taskStatus": "pass",
                "progress": {"percent": 100},
                "tasks": {},
                "partialReport": {"changes": [{"path": "demo.sql"}]},
                "logs": [{"msg": "done"}],
            },
            final_report,
        )

        self.assertTrue(payload["finalReportReady"])
        self.assertEqual(payload["report"], final_report)
        self.assertEqual(payload["partialReport"]["changes"], [{"path": "demo.sql"}])
        self.assertEqual(payload["partialReport"]["finalReport"], final_report)

    def test_normalize_legacy_audit_result_groups_preserves_shape_and_defaults(self):
        payload = normalize_legacy_audit_result_groups(
            {
                "python": [{"file": "demo.py", "line": None, "rule": None, "level": "", "msg": None}],
                "dws": [],
            }
        )

        self.assertEqual(
            payload,
            {
                "python": [{"file": "demo.py", "line": 0, "rule": "", "level": "info", "msg": ""}],
                "dws": [],
            },
        )

    def test_legacy_row_builders_keep_old_audit_results_fields(self):
        nups_rows = build_legacy_nups_audit_result_rows(
            [{"script": "demo.sql", "messages": [{"level": "err", "msg": "bad sql"}]}],
            lambda text: f"rule:{text}",
        )
        fine_rows = build_legacy_fine_audit_result_rows(
            [{"file": "demo.cpt", "issues": [{"rule": "missing-auth", "level": "warn", "msg": "check auth"}]}]
        )

        self.assertEqual(
            nups_rows,
            {
                "nups": [{"file": "demo.sql", "line": 0, "rule": "rule:bad sql", "level": "err", "msg": "bad sql"}]
            },
        )
        self.assertEqual(
            fine_rows,
            {
                "fine": [{"file": "demo.cpt", "line": 0, "rule": "missing-auth", "level": "warn", "msg": "check auth"}]
            },
        )


if __name__ == "__main__":
    unittest.main()
