import unittest

from app.modules.audit.run_result_finalizer import finalize_run_result


class RunResultFinalizerTests(unittest.TestCase):
    def test_keeps_existing_final_report_and_compatibility_sections(self):
        final_report = {"task": {"status": "pass"}, "sections": [{"name": "summary"}]}
        workflow_result = {
            "task": {"status": "pass"},
            "partialReport": {"changes": [{"path": "demo.sql"}]},
            "finalReport": final_report,
            "audit_results": [{"category": "sql", "message": "ok"}],
            "unifiedAssetIssues": [{"rule_code": "missing-root"}],
            "lineageSummary": {
                "resultTables": ["DM.TABLE_A"],
                "jobs": ["JOB_A"],
                "recvPlans": [],
                "sysNames": [],
                "outfiles": [],
                "warnings": [],
                "stats": {},
            },
        }

        result = finalize_run_result(
            workflow_result,
            svn_result={"source_type": "local", "workspace_root": r"C:\workspace\demo"},
            source_ref=r"C:\workspace\demo",
            fallback_source_type="svn",
            logs=[{"level": "INFO", "msg": "done"}],
            build_source_summary=lambda payload, *, source_ref, fallback_source_type: {
                "sourceType": payload.get("source_type", fallback_source_type),
                "sourceRef": source_ref,
                "workspaceRoot": payload.get("workspace_root", ""),
            },
        )

        self.assertIs(result, workflow_result)
        self.assertIs(result["finalReport"], final_report)
        self.assertEqual(result["partialReport"], {"changes": [{"path": "demo.sql"}]})
        self.assertEqual(result["audit_results"], [{"category": "sql", "message": "ok"}])
        self.assertEqual(result["unifiedAssetIssues"], [{"rule_code": "missing-root"}])
        self.assertEqual(result["lineageSummary"]["resultTables"], ["DM.TABLE_A"])
        self.assertEqual(result["sourceType"], "local")
        self.assertEqual(result["sourceRef"], r"C:\workspace\demo")
        self.assertEqual(result["workspaceRoot"], r"C:\workspace\demo")
        self.assertEqual(result["logs"], [{"level": "INFO", "msg": "done"}])

    def test_source_payload_uses_original_summary_builder_contract(self):
        calls = []
        svn_result = {"source_type": "svn", "exported_paths": ["demo.sql"]}

        def build_source_summary(payload, *, source_ref, fallback_source_type):
            calls.append((payload, source_ref, fallback_source_type))
            return {"sourceType": payload["source_type"], "sourceRef": source_ref}

        result = finalize_run_result(
            {"task": {"status": "warn"}},
            svn_result=svn_result,
            source_ref="svn://repo/hcyt/demo",
            fallback_source_type="svn",
            logs=[],
            build_source_summary=build_source_summary,
        )

        self.assertEqual(calls, [(svn_result, "svn://repo/hcyt/demo", "svn")])
        self.assertEqual(result["sourceType"], "svn")
        self.assertEqual(result["sourceRef"], "svn://repo/hcyt/demo")
        self.assertEqual(result["logs"], [])

    def test_does_not_swallow_source_summary_exceptions(self):
        def build_source_summary(*_args, **_kwargs):
            raise RuntimeError("summary failed")

        with self.assertRaisesRegex(RuntimeError, "^summary failed$"):
            finalize_run_result(
                {"task": {"status": "fail"}},
                svn_result={},
                source_ref="svn://repo",
                fallback_source_type="svn",
                logs=[],
                build_source_summary=build_source_summary,
            )


if __name__ == "__main__":
    unittest.main()
