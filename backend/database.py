from __future__ import annotations

import json

from db.connection import connect
from db.profiles import DatabaseProfile, resolve_profile
from db.schema import initialize_schema
from db.tables import render_table_tokens


class CompatRow(dict):
    def __init__(self, columns, values):
        super().__init__(zip(columns, values))
        self._values = tuple(values)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class CompatCursor:
    def __init__(self, cursor, profile: DatabaseProfile, lastrowid=None):
        self._cursor = cursor
        self._profile = profile
        self.lastrowid = lastrowid
        self.rowcount = getattr(cursor, "rowcount", None)

    @property
    def description(self):
        return self._cursor.description

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return self._convert_row(row)

    def fetchall(self):
        return [self._convert_row(row) for row in self._cursor.fetchall()]

    def close(self):
        close = getattr(self._cursor, "close", None)
        if close:
            close()

    def _convert_row(self, row):
        if isinstance(row, CompatRow):
            return row
        if hasattr(row, "keys"):
            return CompatRow(list(row.keys()), [row[key] for key in row.keys()])
        columns = [description[0] for description in (self._cursor.description or [])]
        return CompatRow(columns, row)


class CompatConnection:
    def __init__(self, profile: DatabaseProfile):
        self.profile = profile
        self._connection = connect(profile)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self._connection.commit()
            else:
                self._connection.rollback()
        finally:
            self.close()

    def execute(self, sql, params=(), expect_lastrowid=False):
        cursor = self._connection.cursor()
        sql_to_execute = self._sql_for_insert_id(sql, expect_lastrowid=expect_lastrowid)
        cursor.execute(self._normalize_sql(sql_to_execute), tuple(params or ()))
        lastrowid = self._extract_insert_id(cursor, sql_to_execute)
        return CompatCursor(cursor, self.profile, lastrowid=lastrowid)

    def executemany(self, sql, seq_of_params):
        cursor = self._connection.cursor()
        cursor.executemany(self._normalize_sql(sql), [tuple(params) for params in seq_of_params])
        return CompatCursor(cursor, self.profile)

    def executescript(self, sql_script):
        sql_script = render_table_tokens(sql_script, self.profile)
        cursor = self._connection.cursor()
        for statement in [part.strip() for part in sql_script.split(";") if part.strip()]:
            cursor.execute(self._normalize_sql(statement))
        return CompatCursor(cursor, self.profile)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()

    def _normalize_sql(self, sql):
        return render_table_tokens(sql, self.profile).replace("?", "%s")

    def _sql_for_insert_id(self, sql, expect_lastrowid=False):
        if not expect_lastrowid:
            return sql
        lowered = sql.lower()
        if lowered.lstrip().startswith("insert") and " returning " not in lowered:
            return f"{sql.rstrip()} RETURNING id"
        return sql

    def _extract_insert_id(self, cursor, sql):
        if " returning " not in sql.lower():
            return None
        row = cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return row.get("id")
        if hasattr(row, "keys"):
            return row["id"]
        return row[0]


def get_connection() -> CompatConnection:
    return CompatConnection(resolve_profile())


def execute_insert(sql: str, params=()) -> int:
    with get_connection() as connection:
        cursor = connection.execute(sql, params, expect_lastrowid=True)
        return cursor.lastrowid


def upsert_task_report(task_id: int, report_json: str, created_at: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM {{table:task_reports}} WHERE task_id = ?", (task_id,))
        connection.execute(
            "INSERT INTO {{table:task_reports}} (task_id, report_json, created_at) VALUES (?, ?, ?)",
            (task_id, report_json, created_at),
        )


def init_db() -> None:
    profile = resolve_profile()
    initialize_schema(profile)

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
                (
                    "HCYT Lakehouse Review",
                    "hcyt",
                    "svn://example.com/repos/datawh/branches/demo-hcyt",
                    "hcyt",
                    "DWS / Hive SQL / Python / Scheduling",
                ),
                (
                    "FineReport Review",
                    "fine-report",
                    "https://git.example.com/report/fine-report.git",
                    "fine-report",
                    "Templates / Datasets / Permissions",
                ),
                (
                    "NUPS Unified Payment Review",
                    "nups",
                    "svn://example.com/repos/pay/nups/trunk",
                    "nups",
                    "Contracts / Config / Integration Checks",
                ),
            ],
        )

        connection.executemany(
            """
            INSERT INTO {{table:audit_tasks}} (repo, workflow, status, revision, author, started_at, duration, ai_enabled, debug_enabled, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "svn://example.com/repos/datawh/branches/demo-hcyt",
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
                    "svn://example.com/repos/datawh/branches/demo-hcyt",
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
                    "https://git.example.com/report/fine-report.git",
                    "fine-report",
                    "fail",
                    "8f1c2ad",
                    "liyang",
                    "2026-06-07 15:10:24",
                    "1m12s",
                    1,
                    0,
                    "git",
                ),
            ],
        )
        connection.execute(
            "UPDATE {{table:audit_tasks}} SET source_ref = repo, operator_user = author WHERE source_ref = '' OR operator_user = ''"
        )

        connection.executemany(
            """
            INSERT INTO {{table:audit_results}} (task_id, category, file_name, line_no, rule_name, level, message)
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
            INSERT INTO {{table:fine_report_items}} (
                title, file_path, report_type, change_type, connection_name,
                focus, dataset_sql, dataset_rows, issues_json, ref_tables_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            fine_report_rows,
        )
