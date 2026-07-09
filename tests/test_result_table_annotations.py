import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
SVN_CHECK_DIR = BACKEND_DIR / "svn_check"
for path in (BACKEND_DIR, SVN_CHECK_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from audit.result_normalizer import normalize_table  # noqa: E402
from audit.result_table_annotations import annotate_table, load_result_table_annotations  # noqa: E402


class FakePublicData:
    def all_disabled_result_tables(self):
        return [("dm.table_a",), None, ("",)]

    def all_result_table_sys_names(self):
        return [
            ("dm.table_a", "SYS_A"),
            ("DM.TABLE_A", "SYS_A"),
            ("dm.table_a", " 二代评分卡 "),
            ("dm.table_b", None),
            ("dm.table_c", "SYS_C"),
        ]


class ResultTableAnnotationsTests(unittest.TestCase):
    def test_load_result_table_annotations_keeps_disabled_and_sys_names_shape(self):
        disabled, sys_name_map = load_result_table_annotations(
            safe=lambda _label, fn, _default: fn(),
            public_data=FakePublicData(),
            normalize_table=normalize_table,
        )

        self.assertEqual(disabled, {"DM.TABLE_A"})
        self.assertEqual(sys_name_map["DM.TABLE_A"], ["SYS_A", "二代评分卡"])
        self.assertEqual(sys_name_map["DM.TABLE_C"], ["SYS_C"])

    def test_annotate_table_preserves_disabled_sys_names_and_highlight_behavior(self):
        annotated = annotate_table(
            "dm.table_a",
            {"DM.TABLE_A"},
            {"DM.TABLE_A": ["普通系统"], "DM.TABLE_B": ["二代评分卡"]},
            normalize_table=normalize_table,
            highlight_result_source_systems={"二代评分卡", "IPC系统"},
        )
        highlighted = annotate_table(
            "dm.table_b",
            set(),
            {"DM.TABLE_B": ["二代评分卡"]},
            normalize_table=normalize_table,
            highlight_result_source_systems={"二代评分卡", "IPC系统"},
        )

        self.assertEqual(
            annotated,
            {"name": "DM.TABLE_A", "disabled": True, "sysNames": ["普通系统"], "highlight": True},
        )
        self.assertEqual(
            highlighted,
            {"name": "DM.TABLE_B", "disabled": False, "sysNames": ["二代评分卡"], "highlight": True},
        )

    def test_load_result_table_annotations_degrades_through_safe_fallback(self):
        calls = []

        def safe(label, fn, default):
            calls.append(label)
            if "源系统" in label:
                return default
            return fn()

        disabled, sys_name_map = load_result_table_annotations(
            safe=safe,
            public_data=FakePublicData(),
            normalize_table=normalize_table,
        )

        self.assertEqual(disabled, {"DM.TABLE_A"})
        self.assertEqual(sys_name_map, {})
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
