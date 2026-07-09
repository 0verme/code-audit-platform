import unittest

from backend.audit.hcyt_progress_events import (
    build_lineage_checked_progress,
    build_program_checked_progress,
    build_source_classified_progress,
    publish_hcyt_progress,
)


class HcytProgressEventsTests(unittest.TestCase):
    def test_source_classified_payload_order_is_stable(self):
        self.assertEqual(
            build_source_classified_progress(changes=[{"path": "a"}], conflicts=[{"path": "b"}]),
            [("changes", [{"path": "a"}]), ("conflicts", [{"path": "b"}])],
        )

    def test_program_checked_payload_order_is_stable(self):
        self.assertEqual(
            build_program_checked_progress(
                python_rows=[{"file": "program.py"}],
                py_scripts=[{"script": "program.py"}],
                ref_tables=["DM.TABLE_A"],
                deps=[{"lane": "job"}],
            ),
            [
                ("python", [{"file": "program.py"}]),
                ("pyScripts", [{"script": "program.py"}]),
                ("refTables", ["DM.TABLE_A"]),
                ("deps", [{"lane": "job"}]),
            ],
        )

    def test_lineage_checked_payload_order_is_stable(self):
        lineage = {"resultTables": [], "stats": {}}

        self.assertEqual(
            build_lineage_checked_progress(
                asset_issues=[],
                unified_asset_issues=[],
                lineage_summary=lineage,
            ),
            [
                ("assetIssues", []),
                ("unifiedAssetIssues", []),
                ("lineageSummary", lineage),
            ],
        )

    def test_publish_progress_replays_events_in_order(self):
        calls = []

        publish_hcyt_progress(lambda key, value: calls.append((key, value)), [("a", 1), ("b", None), ("c", [])])

        self.assertEqual(calls, [("a", 1), ("b", None), ("c", [])])


if __name__ == "__main__":
    unittest.main()
