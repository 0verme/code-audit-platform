import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from audit.checks import dependency  # noqa: E402


class SharedGraphDependencyTests(unittest.TestCase):
    def test_parse_job_dependencies_filters_prefix_and_duplicates(self):
        self.assertEqual(
            dependency.parse_job_dependencies("33: JOB_A | 11:SKIP | 33:JOB_B | 33:JOB_A | 33: "),
            ["JOB_A", "JOB_B"],
        )

    def test_build_dependency_graph_keeps_empty_nodes_and_trimmed_dependencies(self):
        graph = dependency.build_dependency_graph(
            [
                (" JOB_A ", "33:JOB_B|33: JOB_C "),
                ("JOB_B", ""),
                ("", "33:JOB_Z"),
                (None, "33:JOB_Z"),
            ]
        )

        self.assertEqual(dict(graph), {"JOB_A": ["JOB_B", "JOB_C"], "JOB_B": [], "JOB_C": []})

    def test_find_cycles_deduplicates_rotations_and_respects_only_nodes_and_max_cycles(self):
        graph = {
            "A": ["B"],
            "B": ["C"],
            "C": ["A", "D"],
            "D": ["C"],
            "E": ["F"],
            "F": ["E"],
        }

        self.assertEqual(dependency.find_cycles(graph, only_nodes={"Z"}), [])
        self.assertEqual(dependency.find_cycles(graph, only_nodes={"D"}), [["C", "D", "C"]])
        self.assertEqual(dependency.find_cycles(graph, max_cycles=2), [["A", "B", "C", "A"], ["C", "D", "C"]])

    def test_build_reverse_dependency_graph_and_find_all_dependent_jobs_keep_current_bfs_shape(self):
        reverse_graph = dependency.build_reverse_dependency_graph(
            [
                ("JOB_A", "33:JOB_B|11:JOB_X|33:JOB_C"),
                ("JOB_B", "33:JOB_D"),
                ("JOB_C", ""),
                ("JOB_D", None),
            ]
        )

        self.assertEqual(dict(reverse_graph), {"JOB_B": ["JOB_A"], "JOB_X": ["JOB_A"], "JOB_C": ["JOB_A"], "JOB_D": ["JOB_B"]})
        self.assertEqual(dependency.find_all_dependent_jobs("JOB_D", reverse_graph), [("JOB_B", 1), ("JOB_A", 2)])
        self.assertEqual(dependency.find_all_dependent_jobs("UNKNOWN", reverse_graph), [])


if __name__ == "__main__":
    unittest.main()
