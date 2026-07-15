# -*- coding: utf-8 -*-
"""Offline self-check for the audit engine.

This helper builds small local sample files and runs the real engine workflows
without requiring SVN. It writes task/report rows through the platform database
compatibility layer.
"""

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.modules.audit.engine as audit_engine  # noqa: E402
from app.db.schema import init_db  # noqa: E402
from app.db.sql_runner import execute_insert  # noqa: E402


DWS_SQL = """\
create table dwuprr.ijep_demo_tbl (
    cust_no VARCHAR2(32),
    bal_amt numeric(18,2)
) TO GROUP GROUP_VERSION1;
alter table dwuprr.ijep_demo_tbl add column dt varchar(8);
insert into dwm.m_demo_target select distinct cust_no from dwuprr.ijep_demo_tbl;
"""

HIVE_SQL = "create table ods.demo_trans (acct_no varchar2(32));\nalter table ods.demo_trans add columns (dt string);\n"

PY_SCRIPT = (
    '"""demo processor"""\n# ' + "x" * 1100 + "\n"
    "SQL = '''\ninsert into DWUPRR.IJEP_DEMO_TBL\nselect distinct t.cust_no, nvl(nvl(t.bal,0),0) bal\n"
    "from DWM.M_DEMO_SOURCE t where t.d_date='20240101'\n'''\nfor i in range(3):\n    pass\n"
)

NUPS_PY = (
    '"""nups demo"""\n# ' + "y" * 1100 + "\n"
    "SQL='''insert into nups_data.t_demo select distinct a from nups_data.src where d_date=to_date('20240101')'''\n"
    "for i in range(2):\n    pass\n"
)

CPT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<WorkBook>
  <TableData name="ds_main">
    <Query>SELECT * FROM DWS.RISK_TAG_D t1, DWM.M_CUST_INFO t2 WHERE cert_no IS NOT NULL</Query>
    <DatabaseName>dev_placeholder</DatabaseName>
  </TableData>
  <Report class="com.fr.report.worksheet.WorkSheet" name="sheet1"/>
</WorkBook>
"""


def make_task(workflow):
    return execute_insert(
        """INSERT INTO {{table:audit_tasks}} (repo, workflow, status, revision, author, started_at,
                                    duration, ai_enabled, debug_enabled, progress, step)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            f"local-selfcheck-{workflow}",
            workflow,
            "running",
            "-",
            "selfcheck",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "0s",
            0,
            0,
            0,
            "selfcheck",
        ),
    )


def svn_stub(root, files):
    return {
        "exported_paths": [str(p) for p in files],
        "branch_changed_files": [str(p.relative_to(root)).replace("\\", "/") for p in files],
        "trunk_conflict_files": [],
        "create_revision": "0",
    }


def dump(report, keys):
    task = report["task"]
    print(f"  status={task['status']} errors={task['errors']} warnings={task.get('warnings')}")
    for key in keys:
        value = report.get(key)
        if isinstance(value, list):
            print(f"  {key}: {len(value)} items")
    print(f"  report_bytes={len(json.dumps(report, ensure_ascii=False))}")


def run_hcyt(root):
    dws = root / "01_demo_dws.sql"
    dws.write_text(DWS_SQL, encoding="utf-8")
    hive = root / "02_demo_hive.sql"
    hive.write_text(HIVE_SQL, encoding="utf-8")
    py_dir = root / "DIDP_PROJECT_WORKSPACE" / "DWUPRR" / "DWS_DWUPRR.IJEP_DEMO_TBL"
    py_dir.mkdir(parents=True)
    py_file = py_dir / "001_DWS_DWUPRR_IJEP_DEMO_TBL_1_00.py"
    py_file.write_text(PY_SCRIPT, encoding="utf-8")
    sbin_dir = root / "Didp" / "sbin" / "CZCB"
    sbin_dir.mkdir(parents=True)
    shell_file = sbin_dir / "post_demo.sh"
    shell_file.write_bytes(b"#!/bin/sh\r\necho demo\r\n")

    task_id = make_task("hcyt")
    run = audit_engine.TaskRun(task_id, "local-selfcheck/hcyt", "hcyt")
    report = run.run_hcyt(svn_stub(root, [dws, hive, py_file, shell_file]))
    report["logs"] = run.logs
    run.finish(report["task"]["status"], report=report)
    print(f"== HCYT task {task_id} ==")
    dump(report, ["dws", "hive", "python", "sbin", "config", "pyScripts", "refTables", "changes"])


def run_nups(root):
    nroot = root / "NUPS_DATA"
    nroot.mkdir()
    py_file = nroot / "001_demo.py"
    py_file.write_text(NUPS_PY, encoding="utf-8")
    sql_file = nroot / "pboc.sql"
    sql_file.write_text("create table nups_data.t (a varchar2(10));\nalter table nups_data.t add b int;\n", encoding="utf-8")

    task_id = make_task("nups")
    run = audit_engine.TaskRun(task_id, "local-selfcheck/nups", "nups")
    report = run.run_nups(svn_stub(root, [py_file, sql_file]))
    report["logs"] = run.logs
    run.finish(report["task"]["status"], report=report)
    print(f"== NUPS task {task_id} ==")
    dump(report, ["sqlChecks", "pyScripts", "changes"])


def run_fine(root):
    froot = root / "fine-report" / "risk"
    froot.mkdir(parents=True)
    cpt = froot / "[R001]demo.cpt"
    cpt.write_text(CPT_XML, encoding="utf-8")

    task_id = make_task("fine-report")
    run = audit_engine.TaskRun(task_id, "local-selfcheck/fine-report", "fine-report")
    report = run.run_fine(svn_stub(root, [cpt]))
    report["logs"] = run.logs
    run.finish(report["task"]["status"], report=report)
    print(f"== FineReport task {task_id} ==")
    dump(report, ["reports", "refTables"])


def main():
    init_db()
    audit_engine._load_real_modules()
    if audit_engine._mods is None:
        raise SystemExit(f"engine import failed:\n{audit_engine._import_error}")

    root = Path(tempfile.mkdtemp(prefix="svncheck_self_"))
    run_hcyt(root)
    run_nups(root)
    run_fine(root)
    print("\nALL PIPELINES OK")


if __name__ == "__main__":
    main()
