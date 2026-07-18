import sys
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.checks.hcyt import sql_rule  # noqa: E402
from app.modules.audit.checks.hcyt.sensitive_sql import scan_sensitive_sql  # noqa: E402


def _scan(sql_text: str, namespace: str = "hcyt.sql"):
    return scan_sensitive_sql(sql_text, namespace=namespace)


def test_grant_is_reported_for_dws_and_hive_with_context():
    sql_text = "\n\nGRANT SELECT ON dwuprr.ijep_police_cdk_detail_r TO dwd_api;"

    for namespace in ("hcyt.sql", "hcyt.hive"):
        findings = _scan(sql_text, namespace)

        assert len(findings) == 1
        assert findings[0].rule_code == f"{namespace}.permission_change"
        assert findings[0].level == "err"
        assert findings[0].location == "第 3 行"
        assert findings[0].evidence == {
            "operation": "GRANT",
            "line": 3,
            "object": "dwuprr.ijep_police_cdk_detail_r",
            "principal": "dwd_api",
        }


def test_permission_and_identity_operations_are_errors():
    findings = _scan(
        """
        REVOKE SELECT ON TABLE dwm.m_customer FROM analyst;
        CREATE USER reviewer;
        ALTER ROLE auditor;
        DROP USER old_user;
        """
    )

    assert [item.rule_code for item in findings] == [
        "hcyt.sql.permission_change",
        "hcyt.sql.identity_change",
        "hcyt.sql.identity_change",
        "hcyt.sql.identity_change",
    ]
    assert all(item.level == "err" for item in findings)
    assert findings[0].evidence["principal"] == "analyst"


def test_destructive_ddl_operations_are_errors():
    findings = _scan(
        """
        DROP DATABASE IF EXISTS demo_db;
        DROP SCHEMA audit;
        DROP TABLE dm.report;
        DROP VIEW dm.report_view;
        DROP MATERIALIZED VIEW dm.report_mv;
        DROP FUNCTION dm.refresh_report;
        DROP INDEX dm.report_idx;
        TRUNCATE TABLE dm.report;
        ALTER TABLE dm.report DROP COLUMN remark;
        ALTER TABLE dm.report DROP IF EXISTS PARTITION (d_date = '20260718');
        """
    )

    assert len(findings) == 10
    assert all(item.rule_code == "hcyt.sql.destructive_ddl" for item in findings)
    assert all(item.level == "err" for item in findings)
    assert findings[0].evidence["object"] == "demo_db"
    assert findings[4].evidence["operation"] == "DROP MATERIALIZED VIEW"
    assert findings[-1].evidence["operation"] == "ALTER TABLE DROP PARTITION"


def test_only_unbounded_update_and_delete_are_reported():
    findings = _scan(
        """
        UPDATE dm.target SET value = 1;
        DELETE FROM dm.target;
        UPDATE dm.target SET value = 2 WHERE id = 1;
        DELETE FROM dm.target WHERE id = 2;
        UPDATE dm.target
           SET value = (SELECT max(value) FROM dm.source WHERE source_id = 1);
        WITH source AS (SELECT id FROM dm.source WHERE enabled = 1)
        DELETE FROM dm.target;
        """
    )

    assert [item.evidence["operation"] for item in findings] == [
        "UPDATE",
        "DELETE",
        "UPDATE",
        "DELETE",
    ]
    assert [item.evidence["object"] for item in findings] == [
        "dm.target",
        "dm.target",
        "dm.target",
        "dm.target",
    ]


def test_overwrite_and_safe_alter_are_warnings():
    findings = _scan(
        """
        INSERT OVERWRITE TABLE dm.target SELECT * FROM dm.source;
        LOAD DATA INPATH '/tmp/demo' OVERWRITE INTO TABLE dm.target;
        ALTER TABLE dm.target ADD COLUMN remark STRING;
        """,
        namespace="hcyt.hive",
    )

    assert [item.rule_code for item in findings] == [
        "hcyt.hive.overwrite_write",
        "hcyt.hive.overwrite_write",
        "hcyt.hive.alter_statement",
    ]
    assert all(item.level == "warn" for item in findings)


def test_comments_literals_and_quoted_identifiers_do_not_trigger_false_positives():
    findings = _scan(
        """
        -- GRANT SELECT ON dm.secret TO someone;
        /* DROP TABLE dm.secret;
           ALTER USER someone; */
        SELECT 'REVOKE role FROM user', "grant", `drop` FROM dm.source;
        SELECT grant_status, drop_reason FROM dm.audit_log
        """
    )

    assert findings == []


def test_multiple_statements_case_line_numbers_and_missing_final_semicolon():
    findings = _scan(
        """
        grant select
          on dm.first to role_a;

        TrUnCaTe dm.second;
        alter table dm.third add column note string
        """
    )

    assert [item.evidence["line"] for item in findings] == [2, 5, 6]
    assert [item.level for item in findings] == ["err", "err", "warn"]


def test_rule_entrypoints_use_shared_scanner():
    sql_text = "GRANT SELECT ON dm.report TO analyst;"
    with (
        patch.object(sql_rule, "read_data_from_file", return_value=sql_text),
        patch.object(sql_rule, "all_view_names", return_value=[]),
        patch.object(sql_rule, "all_function_names", return_value=[]),
        patch.object(sql_rule, "run_dws_ddl_rules", return_value=[]),
    ):
        dws_result = sql_rule.rule_dws("dws.sql")

    with patch.object(sql_rule, "read_data_from_file", return_value=sql_text):
        hive_result = sql_rule.rule_hive("hive.sql")

    assert any(item.rule_code == "hcyt.sql.permission_change" for item in dws_result.findings)
    assert any(item.rule_code == "hcyt.hive.permission_change" for item in hive_result.findings)
