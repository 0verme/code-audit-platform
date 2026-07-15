import unittest
from unittest.mock import Mock, patch

from app.modules.audit.workflow_dispatcher import WorkflowRunContext, run_workflow


class WorkflowDispatcherTests(unittest.TestCase):
    def test_run_workflow_dispatches_to_hcyt_runner(self):
        runtime_context = Mock()

        with patch("app.modules.audit.workflow_dispatcher.run_hcyt", return_value={"task": {"status": "pass"}}) as run_hcyt:
            with patch("app.modules.audit.workflow_dispatcher.run_nups") as run_nups:
                with patch("app.modules.audit.workflow_dispatcher.run_fine") as run_fine:
                    result = run_workflow(
                        WorkflowRunContext(
                            workflow="hcyt",
                            runtime_context=runtime_context,
                        )
                    )

        self.assertEqual(result, {"task": {"status": "pass"}})
        run_hcyt.assert_called_once_with(runtime_context)
        run_nups.assert_not_called()
        run_fine.assert_not_called()

    def test_run_workflow_dispatches_to_nups_runner(self):
        runtime_context = Mock()

        with patch("app.modules.audit.workflow_dispatcher.run_hcyt") as run_hcyt:
            with patch("app.modules.audit.workflow_dispatcher.run_nups", return_value={"task": {"status": "pass"}}) as run_nups:
                with patch("app.modules.audit.workflow_dispatcher.run_fine") as run_fine:
                    result = run_workflow(
                        WorkflowRunContext(
                            workflow="nups",
                            runtime_context=runtime_context,
                        )
                    )

        self.assertEqual(result, {"task": {"status": "pass"}})
        run_hcyt.assert_not_called()
        run_nups.assert_called_once_with(runtime_context)
        run_fine.assert_not_called()

    def test_run_workflow_dispatches_to_fine_report_runner(self):
        runtime_context = Mock()

        with patch("app.modules.audit.workflow_dispatcher.run_hcyt") as run_hcyt:
            with patch("app.modules.audit.workflow_dispatcher.run_nups") as run_nups:
                with patch("app.modules.audit.workflow_dispatcher.run_fine", return_value={"task": {"status": "pass"}}) as run_fine:
                    result = run_workflow(
                        WorkflowRunContext(
                            workflow="fine-report",
                            runtime_context=runtime_context,
                        )
                    )

        self.assertEqual(result, {"task": {"status": "pass"}})
        run_hcyt.assert_not_called()
        run_nups.assert_not_called()
        run_fine.assert_called_once_with(runtime_context)

    def test_run_workflow_falls_back_to_hcyt_for_unknown_workflow(self):
        runtime_context = Mock()

        with patch("app.modules.audit.workflow_dispatcher.run_hcyt", return_value={"task": {"status": "pass"}}) as run_hcyt:
            with patch("app.modules.audit.workflow_dispatcher.run_nups") as run_nups:
                with patch("app.modules.audit.workflow_dispatcher.run_fine") as run_fine:
                    result = run_workflow(
                        WorkflowRunContext(
                            workflow="unknown-workflow",
                            runtime_context=runtime_context,
                        )
                    )

        self.assertEqual(result, {"task": {"status": "pass"}})
        run_hcyt.assert_called_once_with(runtime_context)
        run_nups.assert_not_called()
        run_fine.assert_not_called()

    def test_run_workflow_propagates_branch_exceptions_verbatim(self):
        runtime_context = Mock()

        with patch("app.modules.audit.workflow_dispatcher.run_hcyt", side_effect=RuntimeError("boom")):
            with self.assertRaisesRegex(RuntimeError, "^boom$"):
                run_workflow(
                    WorkflowRunContext(
                        workflow="hcyt",
                        runtime_context=runtime_context,
                    )
                )


if __name__ == "__main__":
    unittest.main()
