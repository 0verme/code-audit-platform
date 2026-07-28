import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.workflows.hcyt.legacy_sync import sync_hcyt_legacy_results  # noqa: E402


def _sample_grouped_rows():
    return {
        "dws": [{"file": "dws.sql", "rule": "", "level": "info", "msg": "dws warning"}],
        "hive": [{"file": "hive.sql", "rule": "", "level": "err", "msg": "hive error"}],
        "python": [{"file": "program.py", "rule": "py-rule", "level": "error", "msg": "python error"}],
        "sbin": [{"file": "sbin", "rule": "", "level": "info", "msg": "sbin warning"}],
        "config": [{"file": "SCHEMA_CONFIG", "rule": "", "level": "err", "msg": "config error"}],
        "recv": [{"file": "recv_json", "rule": "", "level": "info", "msg": "recv warning"}],
    }


class HcytLegacyResultSyncTests(unittest.TestCase):
    def test_legacy_group_keys_and_row_fields_are_forwarded_unchanged(self):
        grouped = _sample_grouped_rows()
        calls = []

        sync_hcyt_legacy_results(calls.append, grouped)

        self.assertEqual(calls, [grouped])
        self.assertIs(calls[0], grouped)
        self.assertEqual(list(calls[0].keys()), ["dws", "hive", "python", "sbin", "config", "recv"])
        for category, rows in calls[0].items():
            self.assertIsInstance(rows, list, category)
            for row in rows:
                self.assertEqual(set(row.keys()), {"file", "rule", "level", "msg"})
                self.assertIn("file", row)
                self.assertIn("rule", row)
                self.assertIn("level", row)
                self.assertIn("msg", row)

    def test_empty_legacy_results_are_forwarded_unchanged(self):
        grouped = {"dws": [], "hive": [], "python": [], "sbin": [], "config": [], "recv": []}
        calls = []

        sync_hcyt_legacy_results(calls.append, grouped)

        self.assertEqual(calls, [grouped])
        self.assertIs(calls[0], grouped)

    def test_save_category_rows_exceptions_propagate(self):
        grouped = _sample_grouped_rows()

        def fail(_grouped):
            raise RuntimeError("db write failed")

        with self.assertRaisesRegex(RuntimeError, "db write failed"):
            sync_hcyt_legacy_results(fail, grouped)

if __name__ == "__main__":
    unittest.main()
