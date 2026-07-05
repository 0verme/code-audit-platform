import sys
import unittest
from pathlib import Path


SVN_CHECK_DIR = Path(__file__).resolve().parents[1] / "backend" / "svn_check"
if str(SVN_CHECK_DIR) not in sys.path:
    sys.path.insert(0, str(SVN_CHECK_DIR))

from core.asset_issue import (  # noqa: E402
    build_issue_hash_key,
    build_issue_key,
    create_audit_asset_issue,
    dedupe_issues,
)


class AuditAssetIssueTests(unittest.TestCase):
    def test_build_issue_key_and_hash_are_stable(self):
        issue_key = build_issue_key(
            issue_type="root_missing",
            source_module="hcyt",
            source_file="demo.sql",
            schema_name="dwm",
            table_name="m_demo",
            field_name="cust_id",
            root_word="cust",
        )

        self.assertEqual(issue_key, "ROOT_MISSING|HCYT|demo.sql|DWM|M_DEMO|CUST_ID|CUST")
        self.assertEqual(build_issue_hash_key(issue_key), build_issue_hash_key(issue_key))
        self.assertEqual(len(build_issue_hash_key(issue_key)), 12)

    def test_create_audit_asset_issue_normalizes_names_and_keeps_chinese(self):
        issue = create_audit_asset_issue(
            issue_type="root_missing",
            issue_title="词根待维护",
            issue_desc="字段 客户编号 存在未维护词根",
            asset_type="root",
            source_module="hcyt",
            source_file=" demo.sql ",
            severity="warning",
            suggestion="去维护",
            portal_module="root-management",
            action_label="去维护词根",
            schema_name="dwm",
            table_name="m_demo",
            field_name="客户_id",
            root_word="客户",
        )

        self.assertEqual(issue.issue_type, "ROOT_MISSING")
        self.assertEqual(issue.schema_name, "DWM")
        self.assertEqual(issue.table_name, "M_DEMO")
        self.assertEqual(issue.field_name, "客户_ID")
        self.assertEqual(issue.root_word, "客户")
        self.assertIn("客户编号", issue.issue_desc)

    def test_empty_values_do_not_raise(self):
        issue = create_audit_asset_issue(
            issue_type=None,
            issue_title=None,
            issue_desc=None,
            asset_type=None,
            source_module=None,
            source_file=None,
            severity=None,
            suggestion=None,
            portal_module=None,
            action_label=None,
        )

        self.assertEqual(issue.issue_key, "||||||")
        self.assertEqual(len(issue.issue_hash_key), 12)

    def test_dedupe_issues_removes_duplicate_issue_keys(self):
        issue_a = create_audit_asset_issue(
            issue_type="asset_table_review",
            issue_title="资产表待核对",
            issue_desc="SQL中引用了待核对资产表",
            asset_type="table",
            source_module="hcyt",
            source_file="demo.py",
            severity="warning",
            suggestion="去核对",
            portal_module="data-warehouse",
            action_label="去核对资产表",
            schema_name="dwm",
            table_name="m_demo",
        )
        issue_b = create_audit_asset_issue(
            issue_type="ASSET_TABLE_REVIEW",
            issue_title="资产表待核对",
            issue_desc="重复描述不影响去重",
            asset_type="table",
            source_module="HCYT",
            source_file="demo.py",
            severity="warning",
            suggestion="去核对",
            portal_module="data-warehouse",
            action_label="去核对资产表",
            schema_name="DWM",
            table_name="M_DEMO",
        )

        self.assertEqual(len(dedupe_issues([issue_a, issue_b])), 1)


if __name__ == "__main__":
    unittest.main()
