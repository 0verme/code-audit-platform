import unittest
from unittest.mock import Mock

from backend.audit.workflow_dispatcher import run_workflow


class WorkflowDispatcherTests(unittest.TestCase):
    def test_run_workflow_dispatches_to_hcyt_runner(self):
        run_hcyt = Mock(return_value={"task": {"status": "pass"}})
        run_nups = Mock()
        run_fine = Mock()

        result = run_workflow(
            "hcyt",
            {"exported_paths": []},
            run_hcyt=run_hcyt,
            run_nups=run_nups,
            run_fine=run_fine,
        )

        self.assertEqual(result, {"task": {"status": "pass"}})
        run_hcyt.assert_called_once_with({"exported_paths": []})
        run_nups.assert_not_called()
        run_fine.assert_not_called()

    def test_run_workflow_dispatches_to_nups_runner(self):
        run_hcyt = Mock()
        run_nups = Mock(return_value={"task": {"status": "pass"}})
        run_fine = Mock()

        result = run_workflow(
            "nups",
            {"exported_paths": []},
            run_hcyt=run_hcyt,
            run_nups=run_nups,
            run_fine=run_fine,
        )

        self.assertEqual(result, {"task": {"status": "pass"}})
        run_hcyt.assert_not_called()
        run_nups.assert_called_once_with({"exported_paths": []})
        run_fine.assert_not_called()

    def test_run_workflow_dispatches_to_fine_report_runner(self):
        run_hcyt = Mock()
        run_nups = Mock()
        run_fine = Mock(return_value={"task": {"status": "pass"}})

        result = run_workflow(
            "fine-report",
            {"exported_paths": []},
            run_hcyt=run_hcyt,
            run_nups=run_nups,
            run_fine=run_fine,
        )

        self.assertEqual(result, {"task": {"status": "pass"}})
        run_hcyt.assert_not_called()
        run_nups.assert_not_called()
        run_fine.assert_called_once_with({"exported_paths": []})

    def test_run_workflow_falls_back_to_hcyt_for_unknown_workflow(self):
        run_hcyt = Mock(return_value={"task": {"status": "pass"}})
        run_nups = Mock()
        run_fine = Mock()

        result = run_workflow(
            "unknown-workflow",
            {"exported_paths": []},
            run_hcyt=run_hcyt,
            run_nups=run_nups,
            run_fine=run_fine,
        )

        self.assertEqual(result, {"task": {"status": "pass"}})
        run_hcyt.assert_called_once_with({"exported_paths": []})
        run_nups.assert_not_called()
        run_fine.assert_not_called()

    def test_run_workflow_propagates_branch_exceptions_verbatim(self):
        run_hcyt = Mock(side_effect=RuntimeError("boom"))

        with self.assertRaisesRegex(RuntimeError, "^boom$"):
            run_workflow(
                "hcyt",
                {"exported_paths": []},
                run_hcyt=run_hcyt,
                run_nups=Mock(),
                run_fine=Mock(),
            )


if __name__ == "__main__":
    unittest.main()
