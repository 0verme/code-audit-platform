from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.connection import get_connection  # noqa: E402
from app.db.schema import init_db  # noqa: E402


def seed_demo_data() -> None:
    init_db()
    with get_connection() as connection:
        project_count = connection.execute("SELECT COUNT(*) FROM {{table:projects}}").fetchone()[0]
        if project_count:
            return

        connection.executemany(
            """
            INSERT INTO {{table:projects}} (name, project_key, repo_path, workflow, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("HCYT Lakehouse Review", "hcyt", "svn://example.com/repos/datawh/branches/demo-hcyt", "hcyt", "DWS / Hive SQL / Python / Scheduling"),
                ("FineReport Review", "fine-report", "https://git.example.com/report/fine-report.git", "fine-report", "Templates / Datasets / Permissions"),
                ("NUPS Unified Payment Review", "nups", "svn://example.com/repos/pay/nups/trunk", "nups", "Contracts / Config / Integration Checks"),
            ],
        )
        connection.executemany(
            """
            INSERT INTO {{table:audit_tasks}} (repo, workflow, status, revision, author, started_at, duration, ai_enabled, debug_enabled, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("svn://example.com/repos/datawh/branches/demo-hcyt", "hcyt", "fail", "r48217", "zhanglei", "2026-06-07 14:22:08", "1m47s", 0, 1, "svn"),
                ("svn://example.com/repos/datawh/branches/demo-hcyt", "hcyt", "pass", "r48231", "wangmin", "2026-06-07 16:40:12", "58s", 1, 0, "svn"),
                ("https://git.example.com/report/fine-report.git", "fine-report", "fail", "8f1c2ad", "liyang", "2026-06-07 15:10:24", "1m12s", 1, 0, "git"),
            ],
        )
        connection.execute(
            "UPDATE {{table:audit_tasks}} SET source_ref = repo, operator_user = author WHERE source_ref = '' OR operator_user = ''"
        )
        connection.executemany(
            """
            INSERT INTO {{table:audit_results}} (task_id, category, file_name, rule_name, level, message)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "dws", "dws_cust_asset_d.sql", "No CREATE VIEW", "err", "DWS layer cannot create views."),
                (1, "dws", "dws_cust_asset_d.sql", "No ALTER TABLE", "err", "Schema changes must go through DDL process."),
                (1, "hive", "dwd_acct_event_i.hql", "Missing partition", "err", "Incremental table is missing dt partition."),
                (1, "python", "load_loan_daily.py", "Hard-coded connection", "err", "Database connection string is hard-coded."),
                (1, "sbin", "post_dws_cust_asset.sh", "Missing set -e", "warn", "Shell script will continue after failures."),
                (1, "config", "dws_loan_balance_sum.json", "Missing field type", "err", "Field loan_amt has no type definition."),
                (1, "recv", "cust_asset_recv.json", "Missing charset", "warn", "File charset is not explicitly declared."),
            ],
        )

        fine_report_rows = [
            (
                "Risk Monitor Daily",
                "fine-report/risk/RPT_RISK_MONITOR_D.cpt",
                "cpt",
                "M",
                "FRDS_oracle_dw",
                "Check SELECT *, permissions, and cartesian join risk.",
                "SELECT * FROM DWS.RISK_TAG_D t1, DWM.M_CUST_INFO t2 WHERE t1.cust_no = t2.cust_no",
                "about 5k",
                json.dumps(
                    [
                        {"cat": "perf", "loc": "ds_main", "rule": "Cartesian join risk", "level": "err", "msg": "Join condition is insufficient and may amplify rows."},
                        {"cat": "perm", "loc": "data permission", "rule": "Overexposed access", "level": "err", "msg": "org_no data permission is not bound."},
                        {"cat": "dataset", "loc": "ds_main", "rule": "SELECT *", "level": "warn", "msg": "List only the fields used by the report."},
                    ],
                    ensure_ascii=False,
                ),
                json.dumps([{"name": "DWS.RISK_TAG_D", "type": "result"}, {"name": "DWM.M_CUST_INFO", "type": "mid"}], ensure_ascii=False),
            ),
            (
                "Loan Balance Summary",
                "fine-report/credit/RPT_LOAN_BAL_SUM.cpt",
                "cpt",
                "M",
                "dev_oracle_192",
                "Verify production connection and partition filter.",
                "SELECT loan_type, SUM(bal_amt) FROM dev_dw.DWS_LOAN_BAL_SUM GROUP BY loan_type",
                "about 2k",
                json.dumps(
                    [
                        {"cat": "conn", "loc": "data source", "rule": "Non-production DB", "level": "err", "msg": "Connection points to development database."},
                        {"cat": "conn", "loc": "ds_bal", "rule": "Hard-coded schema", "level": "err", "msg": "SQL hard-codes dev_dw and is not portable."},
                        {"cat": "perf", "loc": "ds_bal", "rule": "Missing partition filter", "level": "warn", "msg": "dt filter is missing and may full-scan history."},
                    ],
                    ensure_ascii=False,
                ),
                json.dumps([{"name": "DWS.DWS_LOAN_BAL_SUM", "type": "result"}], ensure_ascii=False),
            ),
        ]
        connection.executemany(
            """
            INSERT INTO {{table:fine_report_items}} (
                title, file_path, report_type, change_type, connection_name,
                focus, dataset_sql, dataset_rows, issues_json, ref_tables_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            fine_report_rows,
        )


if __name__ == "__main__":
    seed_demo_data()
