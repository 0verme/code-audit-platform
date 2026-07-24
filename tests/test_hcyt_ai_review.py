import unittest

from app.modules.audit.workflows.hcyt.ai_review import run_hcyt_ai_review, select_hcyt_ai_targets


class HcytAiReviewTests(unittest.TestCase):
    def test_selects_python_targets_before_dws_fallback(self):
        self.assertEqual(
            select_hcyt_ai_targets(py_lists=["program.py"], dws_url="dws.sql"),
            ["program.py"],
        )

    def test_uses_dws_fallback_when_no_python_targets(self):
        self.assertEqual(
            select_hcyt_ai_targets(py_lists=[], dws_url="dws.sql"),
            ["dws.sql"],
        )
        self.assertEqual(select_hcyt_ai_targets(py_lists=[], dws_url=None), [])

    def test_enabled_ai_delegates_to_existing_builder(self):
        updates = []
        calls = []

        result = run_hcyt_ai_review(
            py_lists=["program.py"],
            dws_url="dws.sql",
            errors=2,
            warnings=3,
            ai_enabled=True,
            update_progress=lambda **kwargs: updates.append(kwargs),
            build_ai=lambda targets, errors, warnings, **kwargs: calls.append((targets, errors, warnings, kwargs)) or {"ai": "ok"},
        )

        self.assertEqual(updates, [{"progress": 85, "step": "AI 分析"}])
        self.assertEqual(calls, [(["program.py"], 2, 3, {"workflow": "hcyt"})])
        self.assertEqual(result, {"ai": "ok"})

    def test_disabled_ai_keeps_summary_progress_and_builder_semantics(self):
        updates = []

        result = run_hcyt_ai_review(
            py_lists=[],
            dws_url="dws.sql",
            errors=0,
            warnings=1,
            ai_enabled=False,
            update_progress=lambda **kwargs: updates.append(kwargs),
            build_ai=lambda targets, errors, warnings, **_kwargs: None,
        )

        self.assertEqual(updates, [{"progress": 85, "step": "汇总报告"}])
        self.assertIsNone(result)

    def test_builder_exception_is_not_swallowed(self):
        def broken_builder(*_args, **_kwargs):
            raise RuntimeError("ai failed")

        with self.assertRaisesRegex(RuntimeError, "ai failed"):
            run_hcyt_ai_review(
                py_lists=[],
                dws_url=None,
                errors=0,
                warnings=0,
                ai_enabled=True,
                update_progress=lambda **_kwargs: None,
                build_ai=broken_builder,
            )


if __name__ == "__main__":
    unittest.main()
