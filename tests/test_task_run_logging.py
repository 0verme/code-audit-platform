import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.engine import TaskRun  # noqa: E402


class TaskRunLoggingTests(unittest.TestCase):
    def test_non_debug_run_keeps_summary_but_filters_internal_details(self):
        run = TaskRun(1, "svn://repo", "hcyt", debug_enabled=False)

        run.log("当前步骤：分析文件")
        run.log("[timing] hcyt.rules start")
        run.log("Traceback (most recent call last):\n  internal detail", "ERR", detail=True)

        self.assertEqual([entry["msg"] for entry in run.logs], ["当前步骤：分析文件"])

    def test_debug_run_keeps_internal_details(self):
        run = TaskRun(2, "svn://repo", "hcyt", debug_enabled=True)

        run.log("当前步骤：分析文件")
        run.log("[timing] hcyt.rules start")
        run.log("Traceback (most recent call last):\n  internal detail", "ERR", detail=True)

        self.assertEqual(len(run.logs), 3)
        self.assertIn("[timing]", run.logs[1]["msg"])
        self.assertIn("Traceback", run.logs[2]["msg"])


if __name__ == "__main__":
    unittest.main()
