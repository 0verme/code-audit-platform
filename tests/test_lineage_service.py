import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import ServiceError  # noqa: E402
from app.services.lineage_service import get_task_lineage_subgraph  # noqa: E402


def overlay_report():
    return {
        "task": {"revision": "r42"},
        "metadataProfile": "test",
        "lineageOverlay": {
            "schemaVersion": "1.0",
            "revision": "r42",
            "programs": [
                {
                    "lineageKey": "job:JOB_A", "programPath": "jobs/a.py", "scriptName": "a.py",
                    "jobName": "JOB_A", "resultTable": "DM.A", "inputTables": ["ODS.SOURCE"],
                    "dependencyJobs": [], "disabled": False, "changeType": "modified",
                },
                {
                    "lineageKey": "job:JOB_B", "programPath": "jobs/b.py", "scriptName": "b.py",
                    "jobName": "JOB_B", "resultTable": "DM.B", "inputTables": ["DM.A"],
                    "dependencyJobs": ["JOB_A"], "disabled": False, "changeType": "modified",
                },
            ],
        },
    }


class LineageServiceTests(unittest.TestCase):
    def call(self, root="job:JOB_A", **kwargs):
        baseline = [{
            "jobName": "JOB_C", "programPath": "jobs/c.py", "resultTable": "DM.C",
            "dependencyJobs": ["JOB_B"], "disabled": False,
        }]
        with patch("app.services.lineage_service.get_task", return_value={"id": 7, "workflow": "hcyt"}), patch(
            "app.services.lineage_service.get_report_json", return_value=json.dumps(overlay_report())
        ), patch("app.services.lineage_service.load_baseline_programs", return_value=baseline):
            return get_task_lineage_subgraph(7, root, **kwargs)

    def test_task_wide_overlay_connects_changed_programs_to_production_downstream(self):
        graph = self.call(direction="downstream", depth=5, max_nodes=100)
        names = {node["name"] for node in graph["nodes"]}
        self.assertTrue({"a.py", "b.py", "c.py", "DM.A", "DM.B", "DM.C"}.issubset(names))
        current_edges = [edge for edge in graph["edges"] if edge["evidence"]["type"] == "current_change"]
        self.assertTrue(current_edges)
        self.assertEqual(graph["overlayRevision"], "r42")

    def test_direction_depth_and_node_limit_are_applied(self):
        graph = self.call(root="job:JOB_B", direction="upstream", depth=1, max_nodes=1)
        self.assertEqual(len(graph["nodes"]), 1)
        self.assertTrue(graph["truncated"])

    def test_baseline_failure_degrades_to_overlay(self):
        with patch("app.services.lineage_service.get_task", return_value={"id": 7, "workflow": "hcyt"}), patch(
            "app.services.lineage_service.get_report_json", return_value=json.dumps(overlay_report())
        ), patch("app.services.lineage_service.load_baseline_programs", side_effect=RuntimeError("offline")):
            graph = get_task_lineage_subgraph(7, "job:JOB_A")
        self.assertEqual(graph["diagnostics"][0]["code"], "BASELINE_UNAVAILABLE")
        self.assertIn("a.py", {node["name"] for node in graph["nodes"]})

    def test_validation_and_unknown_roots_are_stable(self):
        with self.assertRaises(ServiceError) as direction_error:
            self.call(direction="sideways")
        self.assertEqual(direction_error.exception.status_code, 422)
        with self.assertRaises(ServiceError) as missing_error:
            self.call(root="job:MISSING")
        self.assertEqual(missing_error.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
