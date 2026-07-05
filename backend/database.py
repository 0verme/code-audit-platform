from __future__ import annotations

import json
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "app.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _migrate_audit_tasks(connection: sqlite3.Connection) -> None:
    """老库平滑升级：补齐任务进度 / 日志相关列。"""
    existing = {row[1] for row in connection.execute("PRAGMA table_info(audit_tasks)").fetchall()}
    for name, ddl in (
        ("progress", "ALTER TABLE audit_tasks ADD COLUMN progress INTEGER NOT NULL DEFAULT 0"),
        ("step", "ALTER TABLE audit_tasks ADD COLUMN step TEXT NOT NULL DEFAULT ''"),
        ("finished_at", "ALTER TABLE audit_tasks ADD COLUMN finished_at TEXT"),
        ("error", "ALTER TABLE audit_tasks ADD COLUMN error TEXT"),
        ("logs_json", "ALTER TABLE audit_tasks ADD COLUMN logs_json TEXT NOT NULL DEFAULT '[]'"),
        ("source_type", "ALTER TABLE audit_tasks ADD COLUMN source_type TEXT NOT NULL DEFAULT 'svn'"),
    ):
        if name not in existing:
            connection.execute(ddl)


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                project_key TEXT NOT NULL,
                repo_path TEXT NOT NULL,
                workflow TEXT NOT NULL,
                description TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo TEXT NOT NULL,
                workflow TEXT NOT NULL,
                status TEXT NOT NULL,
                revision TEXT NOT NULL,
                author TEXT NOT NULL,
                started_at TEXT NOT NULL,
                duration TEXT NOT NULL,
                ai_enabled INTEGER NOT NULL DEFAULT 0,
                debug_enabled INTEGER NOT NULL DEFAULT 0,
                progress INTEGER NOT NULL DEFAULT 0,
                step TEXT NOT NULL DEFAULT '',
                finished_at TEXT,
                error TEXT,
                logs_json TEXT NOT NULL DEFAULT '[]',
                source_type TEXT NOT NULL DEFAULT 'svn'
            );

            CREATE TABLE IF NOT EXISTS task_reports (
                task_id INTEGER PRIMARY KEY,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES audit_tasks(id)
            );

            CREATE TABLE IF NOT EXISTS audit_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                file_name TEXT NOT NULL,
                line_no INTEGER NOT NULL,
                rule_name TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES audit_tasks(id)
            );

            CREATE TABLE IF NOT EXISTS fine_report_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                file_path TEXT NOT NULL,
                report_type TEXT NOT NULL,
                change_type TEXT NOT NULL,
                connection_name TEXT NOT NULL,
                focus TEXT NOT NULL,
                dataset_sql TEXT NOT NULL,
                dataset_rows TEXT NOT NULL,
                issues_json TEXT NOT NULL,
                ref_tables_json TEXT NOT NULL
            );
            """
        )

        _migrate_audit_tasks(connection)

        project_count = connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        if project_count:
            return

        connection.executemany(
            """
            INSERT INTO projects (name, project_key, repo_path, workflow, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    "HCYT Lakehouse Review",
                    "hcyt",
                    "svn://10.18.32.7/datawh/branches/2026Q2/hcyt",
                    "hcyt",
                    "DWS / Hive SQL / Python / Scheduling",
                ),
                (
                    "FineReport Review",
                    "fine-report",
                    "https://git.intra/report/fine-report.git",
                    "fine-report",
                    "Templates / Datasets / Permissions",
                ),
                (
                    "NUPS Unified Payment Review",
                    "nups",
                    "svn://10.18.32.7/pay/nups/trunk",
                    "nups",
                    "Contracts / Config / Integration Checks",
                ),
            ],
        )

        connection.executemany(
            """
            INSERT INTO audit_tasks (repo, workflow, status, revision, author, started_at, duration, ai_enabled, debug_enabled, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "svn://10.18.32.7/datawh/branches/2026Q2/hcyt",
                    "hcyt",
                    "fail",
                    "r48217",
                    "zhanglei",
                    "2026-06-07 14:22:08",
                    "1m47s",
                    0,
                    1,
                    "svn",
                ),
                (
                    "svn://10.18.32.7/datawh/branches/2026Q2/hcyt",
                    "hcyt",
                    "pass",
                    "r48231",
                    "wangmin",
                    "2026-06-07 16:40:12",
                    "58s",
                    1,
                    0,
                    "svn",
                ),
                (
                    "https://git.intra/report/fine-report.git",
                    "fine-report",
                    "fail",
                    "8f1c2ad",
                    "liyang",
                    "2026-06-07 15:10:24",
                    "1m12s",
                    1,
                    0,
                    "svn",
                ),
            ],
        )

        connection.executemany(
            """
            INSERT INTO audit_results (task_id, category, file_name, line_no, rule_name, level, message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "dws", "dws_cust_asset_d.sql", 18, "No CREATE VIEW", "err", "DWS layer cannot create views."),
                (1, "dws", "dws_cust_asset_d.sql", 42, "No ALTER TABLE", "err", "Schema changes must go through DDL process."),
                (1, "hive", "dwd_acct_event_i.hql", 12, "Missing partition", "err", "Incremental table is missing dt partition."),
                (1, "python", "load_loan_daily.py", 88, "Hard-coded connection", "err", "Database connection string is hard-coded."),
                (1, "sbin", "post_dws_cust_asset.sh", 5, "Missing set -e", "warn", "Shell script will continue after failures."),
                (1, "config", "dws_loan_balance_sum.json", 9, "Missing field type", "err", "Field loan_amt has no type definition."),
                (1, "recv", "cust_asset_recv.json", 3, "Missing charset", "warn", "File charset is not explicitly declared."),
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
                json.dumps(
                    [
                        {"name": "DWS.RISK_TAG_D", "type": "result"},
                        {"name": "DWM.M_CUST_INFO", "type": "mid"},
                    ],
                    ensure_ascii=False,
                ),
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
            INSERT INTO fine_report_items (
                title, file_path, report_type, change_type, connection_name,
                focus, dataset_sql, dataset_rows, issues_json, ref_tables_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            fine_report_rows,
        )
