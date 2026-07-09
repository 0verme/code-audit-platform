# -*- coding: utf-8 -*-
"""Initialize metadata schema in the active PostgreSQL or DWS profile."""
from __future__ import annotations

from pathlib import Path

from db.connection import connect
from db.profiles import resolve_profile


BACKEND_DIR = Path(__file__).resolve().parent
SCHEMA_SQL = BACKEND_DIR / "svn_check" / "migrate" / "postgres_schema.sql"
EXPECTED_TABLES = [
    "p_job_hjj",
    "p_program_hjj",
    "p_plan_hjj",
    "p_role_hjj",
    "p_fine_hjj",
    "p_job_outfile",
    "p_para_table_lists",
    "p_recv_dwf",
    "p_recv_ops_mapping",
    "p_term_root",
]


def main():
    profile = resolve_profile()
    print(
        f"target profile={profile.name} type={profile.type} "
        f"db={profile.config['host']}:{profile.config['port']}/{profile.config['database']} "
        f"schema={profile.config['schema']}"
    )

    ddl = SCHEMA_SQL.read_text(encoding="utf-8")
    conn = connect(profile)
    try:
        cur = conn.cursor()
        cur.execute(ddl)
        conn.commit()
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name
            """,
            (profile.config["schema"],),
        )
        created = [row[0] for row in cur.fetchall()]
        print(f"{profile.config['schema']} schema tables ({len(created)}):")
        for name in created:
            cur.execute(
                """
                SELECT count(*)
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                """,
                (profile.config["schema"], name),
            )
            col_count = cur.fetchone()[0]
            print(f"  - {profile.config['schema']}.{name} ({col_count} cols)")
        missing = [table for table in EXPECTED_TABLES if table not in created]
        if missing:
            raise SystemExit(f"missing tables: {missing}")
        print("metadata schema initialized")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
