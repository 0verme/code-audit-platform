import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SVN_CHECK_DIR = Path(__file__).resolve().parents[1] / "backend" / "svn_check"
if str(SVN_CHECK_DIR) not in sys.path:
    sys.path.insert(0, str(SVN_CHECK_DIR))

from core.asset_issue import create_audit_asset_issue  # noqa: E402
from services.portal_link_builder import (  # noqa: E402
    build_data_warehouse_link,
    build_portal_link,
    build_root_management_link,
    get_portal_base_url,
)


class PortalLinkBuilderTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_base_url_returns_empty_links(self):
        self.assertEqual(get_portal_base_url(), "")
        self.assertEqual(build_root_management_link("客户 主档"), "")
        self.assertEqual(build_data_warehouse_link("DWM.M_DEMO"), "")

    @patch.dict(os.environ, {"ASSET_PORTAL_BASE_URL": "https://portal.example.test/"}, clear=True)
    def test_build_portal_link_uses_urlencode_for_root_query(self):
        issue = create_audit_asset_issue(
            issue_type="root_missing",
            issue_title="词根待维护",
            issue_desc="存在未维护词根",
            asset_type="root",
            source_module="hcyt",
            source_file="demo.sql",
            severity="warning",
            suggestion="去维护",
            portal_module="root-management",
            action_label="去维护词根",
            root_word="客户 主档",
        )

        self.assertEqual(
            build_portal_link(issue),
            "https://portal.example.test/root-management?q=%E5%AE%A2%E6%88%B7+%E4%B8%BB%E6%A1%A3",
        )

    @patch.dict(os.environ, {"ASSET_PORTAL_BASE_URL": "https://portal.example.test"}, clear=True)
    def test_build_portal_link_uses_qualified_table_name_for_review(self):
        issue = create_audit_asset_issue(
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

        self.assertEqual(
            build_portal_link(issue),
            "https://portal.example.test/data-warehouse?q=DWM.M_DEMO",
        )


if __name__ == "__main__":
    unittest.main()
