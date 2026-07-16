import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.checks.hcyt import python_rule  # noqa: E402


class HcytPythonRuleTimingTests(unittest.TestCase):
    def _patches(self):
        return (
            patch.object(python_rule, "all_sstb", return_value=[]),
            patch.object(python_rule, "read_data_from_file", return_value="select * from dm.source_table"),
            patch.object(python_rule, "all_view_names", return_value=[("DM.VIEW_A",)]),
            patch.object(python_rule, "all_function_names", return_value=[("DM.FUNC_A",)]),
            patch.object(python_rule, "all_tab_partitions", return_value=[(0,)]),
            patch.object(python_rule, "run_dws_ddl_rules", return_value=[]),
        )

    def test_rule_dws_py_emits_database_and_evaluation_timings(self):
        events = []
        with self._patches()[0], self._patches()[1], self._patches()[2], self._patches()[3], self._patches()[4], self._patches()[5]:
            result = python_rule.rule_dws_py(
                "C:/repo/DWS_DM.TABLE_A/program.py",
                file_name="program.py",
                log_timing=lambda label, phase, **fields: events.append((label, phase, fields)),
            )

        self.assertEqual(len(result), 4)
        labels = {event[0] for event in events}
        self.assertTrue({
            "programs.file.rule.load_sstb",
            "programs.file.rule.read_source",
            "programs.file.rule.load_view_names",
            "programs.file.rule.load_function_names",
            "programs.file.rule.load_partitions",
            "programs.file.rule.evaluate",
        }.issubset(labels))
        for label in labels:
            label_events = [event for event in events if event[0] == label]
            self.assertEqual([event[1] for event in label_events], ["start", "end"])
            self.assertEqual(label_events[-1][2]["file"], "program.py")
            self.assertIn("elapsed_ms", label_events[-1][2])

    def test_rule_dws_py_keeps_legacy_call_shape_without_timing(self):
        with self._patches()[0], self._patches()[1], self._patches()[2], self._patches()[3], self._patches()[4], self._patches()[5]:
            result = python_rule.rule_dws_py("C:/repo/DWS_DM.TABLE_A/program.py")

        self.assertEqual(len(result), 4)

    def test_rule_dws_py_reuses_task_metadata_cache(self):
        metadata_cache = {}
        with self._patches()[0] as sstb, self._patches()[1], self._patches()[2] as views, self._patches()[3] as functions, self._patches()[4] as partitions, self._patches()[5]:
            for _ in range(2):
                python_rule.rule_dws_py(
                    "C:/repo/DWS_DM.TABLE_A/program.py",
                    metadata_cache=metadata_cache,
                )

        self.assertEqual(sstb.call_count, 1)
        self.assertEqual(views.call_count, 1)
        self.assertEqual(functions.call_count, 1)
        self.assertEqual(partitions.call_count, 1)

    def test_rule_dws_py_uses_prefetched_partition_count(self):
        metadata_cache = {"partition_counts": {"DM.TABLE_A": 1}}
        with self._patches()[0], self._patches()[1], self._patches()[2], self._patches()[3], self._patches()[4] as partitions, self._patches()[5]:
            result = python_rule.rule_dws_py(
                "C:/repo/DWS_DM.TABLE_A/program.py",
                metadata_cache=metadata_cache,
            )

        self.assertEqual(partitions.call_count, 0)
        self.assertIn("分区表应该增加分区步骤", result[0])


if __name__ == "__main__":
    unittest.main()
