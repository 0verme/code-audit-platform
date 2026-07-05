import sys
import unittest
from pathlib import Path


SVN_CHECK_DIR = Path(__file__).resolve().parents[1] / "backend" / "svn_check"
if str(SVN_CHECK_DIR) not in sys.path:
    sys.path.insert(0, str(SVN_CHECK_DIR))

from core.asset_issue import (  # noqa: E402
    asset_issue_to_unified_issue,
    asset_issues_to_unified_issues,
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

    def test_unified_root_missing_issue_from_object(self):
        issue = create_audit_asset_issue(
            issue_type="root_missing",
            issue_title="Root is missing",
            issue_desc="Field uses an unmaintained root word",
            asset_type="root",
            source_module="hcyt",
            source_file="dws.sql",
            severity="warning",
            suggestion="Maintain the missing root word",
            portal_module="root-management",
            action_label="Do not expose as action",
            schema_name="dwm",
            table_name="m_customer",
            field_name="customer_id",
            root_word="customer",
            portal_url="https://example.test/roots/customer",
        )

        unified = asset_issue_to_unified_issue(issue, scan_batch_id="task-1")

        self.assertEqual(unified["rule_code"], "ROOT_MISSING")
        self.assertEqual(unified["asset_type"], "root")
        self.assertEqual(unified["asset_key"], "CUSTOMER")
        self.assertEqual(unified["portal_action"], "edit_root")
        self.assertEqual(unified["scan_batch_id"], "task-1")
        self.assertEqual(unified["fix_url"], "https://example.test/roots/customer")
        self.assertEqual(unified["evidence"]["root_word"], "CUSTOMER")
        self.assertEqual(unified["evidence"]["schema_name"], "DWM")
        self.assertEqual(unified["evidence"]["table_name"], "M_CUSTOMER")
        self.assertEqual(unified["evidence"]["field_name"], "CUSTOMER_ID")

    def test_unified_asset_table_review_issue_from_object(self):
        issue = create_audit_asset_issue(
            issue_type="asset_table_review",
            issue_title="Asset table needs review",
            issue_desc="Created table should be reviewed in asset portal",
            asset_type="table",
            source_module="hcyt",
            source_file="demo.py",
            severity="warning",
            suggestion="Review the created table",
            portal_module="data-warehouse",
            action_label="Do not expose as action",
            schema_name="dwm",
            table_name="m_customer",
        )

        unified = asset_issue_to_unified_issue(issue)

        self.assertEqual(unified["rule_code"], "ASSET_TABLE_REVIEW")
        self.assertEqual(unified["asset_type"], "table")
        self.assertEqual(unified["asset_key"], "DWM.M_CUSTOMER")
        self.assertEqual(unified["asset_name"], "DWM.M_CUSTOMER")
        self.assertEqual(unified["portal_action"], "review_table")
        self.assertEqual(unified["evidence"]["schema_name"], "DWM")
        self.assertEqual(unified["evidence"]["table_name"], "M_CUSTOMER")
        self.assertEqual(unified["evidence"]["source_file"], "demo.py")

    def test_unified_issue_accepts_camel_case_dict(self):
        unified = asset_issue_to_unified_issue(
            {
                "issueType": "ROOT_MISSING",
                "issueTitle": "Root is missing",
                "issueDesc": "Missing root",
                "assetType": "root",
                "sourceModule": "hcyt",
                "sourceFile": "dws.sql",
                "severity": "",
                "suggestion": "Maintain it",
                "portalModule": "root-management",
                "schemaName": "DWM",
                "tableName": "M_CUSTOMER",
                "fieldName": "CUSTOMER_ID",
                "rootWord": "CUSTOMER",
                "issueKey": "ROOT_MISSING|HCYT|dws.sql|DWM|M_CUSTOMER|CUSTOMER_ID|CUSTOMER",
                "hashKey": "abc123",
                "portalUrl": "",
            },
            scan_batch_id="task-2",
            created_at="2026-07-05 12:00:00",
        )

        self.assertEqual(unified["issue_id"], "task-2:abc123")
        self.assertEqual(unified["severity"], "warning")
        self.assertEqual(unified["asset_key"], "CUSTOMER")
        self.assertEqual(unified["created_at"], "2026-07-05 12:00:00")

    def test_unified_issues_empty_input_returns_empty_list(self):
        self.assertEqual(asset_issues_to_unified_issues([]), [])


if __name__ == "__main__":
    unittest.main()
