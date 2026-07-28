import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.workflows.hcyt.rule_runner import run_hcyt_rules  # noqa: E402
from app.modules.audit.shared.findings import CheckResult  # noqa: E402


class FakeReService:
    def get_filename(self, path):
        return Path(path).name

    def read_data_from_file(self, path):
        return ""


class FakeHcyt:
    def rule_dws(self, path):
        result = CheckResult()
        result.add("hcyt.sql.demo", "DWS 示例", "info", "dws warning")
        return result

    def rule_hive(self, path):
        result = CheckResult()
        result.add("hcyt.hive.demo", "Hive 示例", "info", "hive warning")
        return result

    def rule_sbin(self, paths):
        return CheckResult()

    def rule_recv_json(self, paths):
        return CheckResult()

    def rule_config(self, paths):
        return CheckResult()

    def rule_dwo(self, path):
        return CheckResult()

    def rule_dwf(self, path):
        return CheckResult()


class FakeModules:
    def __init__(self):
        self.re_service = FakeReService()
        self.hcyt = FakeHcyt()
        self.hcyt_ddl_rule = type("FakeDdlRule", (), {"collect_root_missing_issues": staticmethod(lambda *args: [])})()
        self.hcyt_sql_rule = type(
            "FakeSqlRule",
            (),
            {"collect_created_table_review_issues": staticmethod(lambda *args: [])},
        )()


class HcytRuleRunnerContractTests(unittest.TestCase):
    def test_partial_keys_and_task_order_remain_stable(self):
        grouped = {key: [] for key in ("dws", "hive", "python", "sbin", "config", "recv")}
        partial_order = []
        task_events = []

        run_hcyt_rules(
            "C:/repo/dws.sql",
            "C:/repo/hive.sql",
            ["C:/repo/schema_config.json"],
            ["C:/repo/post.sh"],
            ["C:/repo/recv.json"],
            [],
            [],
            safe=lambda _label, fn, _default: fn(),
            modules=FakeModules(),
            grouped=grouped,
            task_running=lambda key: task_events.append(("running", key)),
            task_success=lambda key, result=None, summary=None: task_events.append(("success", key, result, summary)),
            task_skipped=lambda key, reason=None: task_events.append(("skipped", key, reason)),
            set_partial=lambda key, value: partial_order.append(key),
            download_url=lambda path: f"download://{Path(path).name}",
            build_config_files=lambda paths: [{"path": path} for path in paths],
        )

        self.assertEqual(
            partial_order,
            ["sqlChecks", "dws", "sqlChecks", "hive", "sbin", "recv", "configFiles", "config"],
        )
        self.assertEqual(
            [event[:2] for event in task_events],
            [
                ("running", "dws_sql"),
                ("success", "dws_sql"),
                ("running", "hive_sql"),
                ("success", "hive_sql"),
                ("running", "post_scripts"),
                ("success", "post_scripts"),
                ("running", "recv_config"),
                ("success", "recv_config"),
                ("running", "config_files"),
                ("success", "config_files"),
            ],
        )
        self.assertEqual(set(grouped.keys()), {"dws", "hive", "python", "sbin", "config", "recv"})
        for key in ("dws", "hive", "sbin", "config", "recv"):
            self.assertIsInstance(grouped[key], list)


if __name__ == "__main__":
    unittest.main()
