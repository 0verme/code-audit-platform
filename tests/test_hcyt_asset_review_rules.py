import sys
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config.audit_rules import refresh_audit_rules  # noqa: E402
from app.modules.audit.checks.hcyt import python_rule, sql_rule  # noqa: E402
from app.modules.audit.checks.hcyt.ddl_rule import is_asset_review_required_table  # noqa: E402


def test_python_asset_review_issues_only_include_required_schemas():
    issues = python_rule.build_asset_table_review_issues(
        [
            "dwm.m_customer",
            "DWA.A_ACCOUNT",
            "dm.report_result",
            "DWP.P_LOAN",
            "DWF.F_EVENT",
            "NO_SCHEMA",
            "DWM.M_CUSTOMER",
        ],
        "hcyt",
        "program.py",
    )

    assert [(issue.schema_name, issue.table_name) for issue in issues] == [
        ("DWM", "M_CUSTOMER"),
        ("DWA", "A_ACCOUNT"),
        ("DM", "REPORT_RESULT"),
    ]


def test_sql_asset_review_issues_only_include_required_schemas():
    sql_text = """
        CREATE TABLE DWM.M_CUSTOMER (ID INT);
        CREATE TABLE dwa.a_account (ID INT);
        CREATE TABLE DM.REPORT_RESULT (ID INT);
        CREATE TABLE DWP.P_LOAN (ID INT);
        CREATE TABLE DWF.F_EVENT (ID INT);
        CREATE TABLE NO_SCHEMA (ID INT);
    """

    with patch.object(sql_rule, "read_data_from_file", return_value=sql_text):
        issues = sql_rule.collect_created_table_review_issues("dws.sql")

    assert [(issue.schema_name, issue.table_name) for issue in issues] == [
        ("DWM", "M_CUSTOMER"),
        ("DWA", "A_ACCOUNT"),
        ("DM", "REPORT_RESULT"),
    ]


def test_asset_review_schema_config_can_override_defaults(tmp_path: Path):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        "dws:\n  naming:\n    asset_review_required_schemas: [dwp]\n",
        encoding="utf-8",
    )

    try:
        refresh_audit_rules(path=rules_file)
        assert is_asset_review_required_table("DWP.P_LOAN")
        assert not is_asset_review_required_table("DWM.M_CUSTOMER")
    finally:
        refresh_audit_rules(path=tmp_path / "missing.yaml")


def test_asset_review_schema_defaults_are_used_without_config(tmp_path: Path):
    refresh_audit_rules(path=tmp_path / "missing.yaml")

    assert is_asset_review_required_table("DWM.M_CUSTOMER")
    assert is_asset_review_required_table("dwa.a_account")
    assert is_asset_review_required_table("DM.REPORT_RESULT")
    assert not is_asset_review_required_table("DWP.P_LOAN")
    assert not is_asset_review_required_table("NO_SCHEMA")
