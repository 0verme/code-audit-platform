# -*- coding: utf-8 -*-
"""离线自检：跳过 SVN 拉取，用本地构造样例文件直接跑三条规则流水线。

验证「拷贝进来的真实规则引擎 → engine 编排 → report JSON」整条链路，
在无行内 SVN / GaussDB / JVM 的环境也能跑（依赖数据库的部分自动降级）。
运行：python dev_selfcheck.py
"""
import json
import tempfile
from datetime import datetime
from pathlib import Path

from database import get_connection, init_db
import engine

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
    '"""demo 加工程序"""\n# ' + "x" * 1100 + "\n"
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
    <Query>SELECT * FROM DWS.RISK_TAG_D t1, DWM.M_CUST_INFO t2 WHERE 身份证号 IS NOT NULL</Query>
    <DatabaseName>dev_oracle_192</DatabaseName>
  </TableData>
  <Report class="com.fr.report.worksheet.WorkSheet" name="sheet1"/>
</WorkBook>
"""


def make_task(workflow):
    with get_connection() as connection:
        cur = connection.execute(
            """INSERT INTO audit_tasks (repo, workflow, status, revision, author, started_at,
                                        duration, ai_enabled, debug_enabled, progress, step)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (f"local-selfcheck-{workflow}", workflow, "running", "-", "selfcheck",
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "0秒", 0, 0, 0, "自检"))
        return cur.lastrowid


def svn_stub(root, files):
    return {
        "exported_paths": [str(p) for p in files],
        "branch_changed_files": [str(p.relative_to(root)).replace("\\", "/") for p in files],
        "trunk_conflict_files": [],
        "create_revision": "0",
    }


def dump(report, keys):
    t = report["task"]
    print(f"  status={t['status']} errors={t['errors']} warnings={t.get('warnings')}")
    for k in keys:
        v = report.get(k)
        if isinstance(v, list):
            print(f"  {k}: {len(v)} 项")
    print(f"  report字节数={len(json.dumps(report, ensure_ascii=False))}")


def main():
    init_db()
    engine._load_real_modules()
    if engine._mods is None:
        raise SystemExit(f"引擎加载失败:\n{engine._import_error}")
    root = Path(tempfile.mkdtemp(prefix="svncheck_self_"))

    # ---- HCYT ----
    dws = root / "01_demo_dws.sql"; dws.write_text(DWS_SQL, encoding="utf-8")
    hive = root / "02_demo_hive.sql"; hive.write_text(HIVE_SQL, encoding="utf-8")
    py_dir = root / "DIDP_PROJECT_WORKSPACE" / "DWUPRR" / "DWS_DWUPRR.IJEP_DEMO_TBL"
    py_dir.mkdir(parents=True)
    pyf = py_dir / "001_DWS_DWUPRR_IJEP_DEMO_TBL_1_00.py"; pyf.write_text(PY_SCRIPT, encoding="utf-8")
    sbin_dir = root / "Didp" / "sbin" / "CZCB"; sbin_dir.mkdir(parents=True)
    sh = sbin_dir / "post_demo.sh"; sh.write_bytes(b"#!/bin/sh\r\necho demo\r\n")
    files = [dws, hive, pyf, sh]
    tid = make_task("hcyt")
    run = engine.TaskRun(tid, "local-selfcheck/hcyt", "hcyt")
    rep = run.run_hcyt(svn_stub(root, files)); rep["logs"] = run.logs
    run.finish(rep["task"]["status"], report=rep)
    print(f"== HCYT task {tid} ==")
    dump(rep, ["dws", "hive", "python", "sbin", "config", "pyScripts", "refTables", "changes"])
    print(f"  schedule.tables keys={list(rep['schedule']['tables'].keys())} sqlChecks={list(rep['sqlChecks'].keys())}")

    # ---- NUPS ----
    nroot = root / "NUPS_DATA"; nroot.mkdir()
    npy = nroot / "001_demo.py"; npy.write_text(NUPS_PY, encoding="utf-8")
    nsql = nroot / "pboc.sql"; nsql.write_text("create table nups_data.t (a varchar2(10));\nalter table nups_data.t add b int;\n", encoding="utf-8")
    tid = make_task("nups")
    run = engine.TaskRun(tid, "local-selfcheck/nups", "nups")
    rep = run.run_nups(svn_stub(root, [npy, nsql])); rep["logs"] = run.logs
    run.finish(rep["task"]["status"], report=rep)
    print(f"== NUPS task {tid} ==")
    dump(rep, ["sqlChecks", "pyScripts", "changes"])

    # ---- FineReport ----
    froot = root / "fine-report" / "risk"; froot.mkdir(parents=True)
    cpt = froot / "[R001]demo.cpt"; cpt.write_text(CPT_XML, encoding="utf-8")
    tid = make_task("fine-report")
    run = engine.TaskRun(tid, "local-selfcheck/fine-report", "fine-report")
    rep = run.run_fine(svn_stub(root, [cpt])); rep["logs"] = run.logs
    run.finish(rep["task"]["status"], report=rep)
    print(f"== FineReport task {tid} ==")
    dump(rep, ["reports", "refTables"])
    if rep["reports"]:
        r0 = rep["reports"][0]
        print(f"  report0: conn={r0['conn']} engine={r0['engine']} sheets={r0['sheets']} preview={'有' if r0['previewUrl'] else '无'} issues={len(r0['issues'])}")
    print("\nALL PIPELINES OK")


if __name__ == "__main__":
    main()
