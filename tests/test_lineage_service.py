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

    def test_graph_stops_at_the_current_program_result_table(self):
        graph = self.call()
        names = {node["name"] for node in graph["nodes"]}
        self.assertEqual(names, {"a.py", "ODS.SOURCE", "DM.A"})
        self.assertFalse(graph["truncated"])
        current_edges = [edge for edge in graph["edges"] if edge["evidence"]["type"] == "current_change"]
        self.assertTrue(current_edges)
        self.assertEqual(graph["overlayRevision"], "r42")

    def test_direct_input_and_schedule_dependency_share_one_table_node(self):
        graph = self.call(root="job:JOB_B")
        dm_a_nodes = [node for node in graph["nodes"] if node["name"] == "DM.A"]
        dm_a_edges = [edge for edge in graph["edges"] if edge["sourceId"] == dm_a_nodes[0]["id"]]
        self.assertEqual(len(dm_a_nodes), 1)
        self.assertEqual(
            {edge["kind"] for edge in dm_a_edges},
            {"script_reads_table", "schedule_dependency"},
        )
        self.assertEqual(
            {node["name"] for node in graph["nodes"]},
            {"b.py", "DM.A", "DM.B"},
        )

    def test_baseline_failure_degrades_to_overlay(self):
        with patch("app.services.lineage_service.get_task", return_value={"id": 7, "workflow": "hcyt"}), patch(
            "app.services.lineage_service.get_report_json", return_value=json.dumps(overlay_report())
        ), patch("app.services.lineage_service.load_baseline_programs", side_effect=RuntimeError("offline")):
            graph = get_task_lineage_subgraph(7, "job:JOB_A")
        self.assertEqual(graph["diagnostics"][0]["code"], "BASELINE_UNAVAILABLE")
        self.assertIn("a.py", {node["name"] for node in graph["nodes"]})

    def test_unassociated_program_without_inputs_or_result_is_an_isolated_root(self):
        report = overlay_report()
        report["lineageOverlay"]["programs"] = [{
            "lineageKey": "program:jobs/standalone.py",
            "programPath": "jobs/standalone.py",
            "scriptName": "standalone.py",
            "jobName": "",
            "resultTable": "",
            "inputTables": [],
            "dependencyJobs": [],
            "disabled": False,
            "changeType": "modified",
        }]
        with patch("app.services.lineage_service.get_task", return_value={"id": 7, "workflow": "hcyt"}), patch(
            "app.services.lineage_service.get_report_json", return_value=json.dumps(report)
        ), patch("app.services.lineage_service.load_baseline_programs", return_value=[]):
            graph = get_task_lineage_subgraph(7, "program:jobs/standalone.py")
        self.assertEqual([node["name"] for node in graph["nodes"]], ["standalone.py"])
        self.assertEqual(graph["edges"], [])
        self.assertFalse(graph["truncated"])

    def test_unknown_roots_are_stable(self):
        with self.assertRaises(ServiceError) as missing_error:
            self.call(root="job:MISSING")
        self.assertEqual(missing_error.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
