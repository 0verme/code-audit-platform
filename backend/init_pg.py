# -*- coding: utf-8 -*-
"""把 svn_check 规则引擎所需的 dwp.p_* 元数据表建进 Postgres（幂等）。

连接参数读取 backend/svn_check/configs/database.yaml 的 postgres 段
（可用 SVN_CHECK_PG_* 环境变量覆盖）。DDL 见 svn_check/migrate/postgres_schema.sql。
运行：python init_pg.py
"""
import sys
from pathlib import Path

SVN_CHECK_DIR = Path(__file__).resolve().parent / "svn_check"
sys.path.insert(0, str(SVN_CHECK_DIR))

from shared.db import postgres  # noqa: E402

SCHEMA_SQL = SVN_CHECK_DIR / "migrate" / "postgres_schema.sql"
EXPECTED_TABLES = [
    "p_job_hjj", "p_program_hjj", "p_plan_hjj", "p_role_hjj", "p_fine_hjj",
    "p_job_outfile", "p_para_table_lists", "p_recv_dwf", "p_recv_ops_mapping",
    "p_term_root",
]


def main():
    config = postgres.load_pg_config()
    print(f"目标 PG: {config.get('host')}:{config.get('port')}/{config.get('dbname')} schema=dwp")

    ddl = SCHEMA_SQL.read_text(encoding="utf-8")
    conn = postgres.connect()
    try:
        cur = conn.cursor()
        cur.execute(ddl)
        conn.commit()
        # 核对
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'dwp' ORDER BY table_name"
        )
        created = [row[0] for row in cur.fetchall()]
        print(f"dwp schema 现有表（{len(created)}）：")
        for name in created:
            cur.execute(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_schema='dwp' AND table_name=%s", (name,))
            col_count = cur.fetchone()[0]
            print(f"  - dwp.{name}  ({col_count} 列)")
        missing = [t for t in EXPECTED_TABLES if t not in created]
        if missing:
            print("缺失表：", missing)
            sys.exit(1)
        print("\n全部表已就绪。")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
