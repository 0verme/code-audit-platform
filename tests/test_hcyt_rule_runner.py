import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.hcyt_rule_runner import run_hcyt_rules  # noqa: E402
from app.modules.audit.result_normalizer import text_to_rows  # noqa: E402


class FakeReService:
    def get_filename(self, path):
        return Path(path).name

    def read_data_from_file(self, path):
        return "create table dm.table_a(id int)"


class FakeHcyt:
    def rule_dws(self, path):
        return ("dws info", "", 0)

    def rule_hive(self, path):
        return ("", "hive error", 0)

    def rule_sbin(self, paths):
        return ("sbin info", "", 0)

    def rule_recv_json(self, paths):
        return ("recv info", "", 0)

    def rule_config(self, paths):
        return ("", "config error", 0)

    def rule_dwo(self, path):
        return ("dwo info", "", 0)

    def rule_dwf(self, path):
        return ("", "dwf error", 0)


class FakeDdlRule:
    def collect_root_missing_issues(self, sql_text, source_module, source_file):
        return [{"rule": "root-missing", "source": source_file}]


class FakeSqlRule:
    def collect_created_table_review_issues(self, path, source_module, source_file):
        return [{"rule": "asset-review", "source": source_file}]


class FakeModules:
    def __init__(self):
        self.re_service = FakeReService()
        self.hcyt = FakeHcyt()
        self.hcyt_ddl_rule = FakeDdlRule()
        self.hcyt_sql_rule = FakeSqlRule()
        self.text_to_rows = text_to_rows


class HcytRuleRunnerTests(unittest.TestCase):
    def _run(self, **overrides):
        grouped = {key: [] for key in ("dws", "hive", "python", "sbin", "config", "recv")}
        partials = []
        events = []
        modules = FakeModules()

        def safe(_label, fn, default):
            return fn()

        sql_checks, asset_issues, config_files = run_hcyt_rules(
            overrides.get("dws_url", "C:/repo/dws.sql"),
            overrides.get("hive_url", "C:/repo/hive.sql"),
            overrides.get("schame_config_lists", ["C:/repo/schema_config.json"]),
            overrides.get("sbin_lists", ["C:/repo/sbin/post.sh"]),
            overrides.get("recv_lists", ["C:/repo/recv.json"]),
            overrides.get("dwo_lists", ["C:/repo/task.dwo"]),
            overrides.get("dwf_lists", ["C:/repo/task.dwf"]),
            safe=overrides.get("safe", safe),
            modules=modules,
            grouped=grouped,
            task_running=lambda key: events.append(("running", key)),
            task_success=lambda key, result=None, summary=None: events.append(("success", key, result, summary)),
            task_skipped=lambda key, reason=None: events.append(("skipped", key, reason)),
            set_partial=lambda key, value: partials.append((key, value)),
            download_url=lambda path: f"download://{Path(path).name}",
            build_config_files=lambda paths: [{"path": path, "rows": []} for path in paths],
        )
        return grouped, partials, events, sql_checks, asset_issues, config_files

    def test_run_hcyt_rules_aggregates_results_and_assets(self):
        grouped, partials, events, sql_checks, asset_issues, config_files = self._run()

        self.assertEqual(list(sql_checks.keys()), ["dws", "hive"])
        self.assertEqual(set(grouped.keys()), {"dws", "hive", "python", "sbin", "config", "recv"})
        self.assertEqual(
            [key for key, _value in partials],
            ["sqlChecks", "dws", "sqlChecks", "hive", "sbin", "recv", "config", "configFiles"],
        )
        self.assertEqual(partials[0][1]["dws"]["downloadUrl"], "download://dws.sql")
        self.assertEqual(partials[2][1]["dws"]["downloadUrl"], "download://dws.sql")
        self.assertEqual(
            [event[:2] for event in events if event[0] != "skipped"],
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
        self.assertEqual(len(asset_issues), 2)
        self.assertEqual(config_files, [{"path": "C:/repo/schema_config.json", "rows": []}])
        self.assertEqual(len(grouped["python"]), 2)

    def test_run_hcyt_rules_degrades_single_rule_via_safe_without_changing_shape(self):
        def safe(label, fn, default):
            if label == "hive.sql 规则":
                return default
            return fn()

        grouped, _partials, events, sql_checks, _asset_issues, _config_files = self._run(safe=safe)

        self.assertEqual(sql_checks["hive"]["script"], "hive.sql")
        self.assertEqual(grouped["hive"], [])
        hive_success = [event for event in events if event[:2] == ("success", "hive_sql")][0]
        self.assertEqual(hive_success[3], {"issues": 0})

    def test_run_hcyt_rules_keeps_empty_inputs_and_skip_order(self):
        grouped, partials, events, sql_checks, asset_issues, config_files = self._run(
            dws_url=None,
            hive_url=None,
            schame_config_lists=[],
            sbin_lists=[],
            recv_lists=[],
            dwo_lists=[],
            dwf_lists=[],
        )

        self.assertEqual(grouped, {key: [] for key in ("dws", "hive", "python", "sbin", "config", "recv")})
        self.assertEqual(partials, [])
        self.assertEqual(sql_checks, {})
        self.assertEqual(asset_issues, [])
        self.assertEqual(config_files, [])
        self.assertEqual(
            events,
            [
                ("skipped", "dws_sql", "no dws.sql file"),
                ("skipped", "hive_sql", "no hive.sql file"),
                ("skipped", "post_scripts", "no post script files"),
                ("skipped", "recv_config", "no recv config files"),
                ("skipped", "config_files", "no schema config files"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
