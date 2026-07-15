from types import SimpleNamespace

import pandas as pd

from app.modules.audit.checks import re_service
from app.modules.audit.engine import _build_lineage_summary_payload
from app.modules.audit.hcyt_program_runner import _load_lineage_metadata


def _row(job, dependency, path):
    row = [""] * 33
    row[2] = job
    row[27] = dependency
    row[32] = path
    return tuple(row)


def test_scoped_lineage_keeps_report_shape_without_scanning_all_merge_rows():
    rows = [_row("JOB_TARGET", "33:JOB_DEP", "/etl/DWS.TARGET/target.py")]
    rows.extend(_row(f"JOB_{index}", "", f"/etl/other_{index}.py") for index in range(31_105))
    merge_df = pd.DataFrame(rows)
    dependency_lookup = {"JOB_DEP": "DWS.DEP_TABLE"}

    summary = re_service.build_wide_table_lineage_summary(
        merge_df=merge_df,
        matched_rows=[rows[0]],
        dependency_lookup=dependency_lookup,
        job_outfile_rows=[("JOB_DEP", "dep.out")],
        result_table_recv_detail_rows=[("DWS.DEP_TABLE", "PLAN_A", "SYS_A")],
        result_table_sys_name_rows=[],
        recv_mapping_plan_rows=[],
    )

    assert set(("resultTables", "jobs", "recvPlans", "sysNames", "outfiles", "warnings", "stats")) <= set(summary)
    assert summary["jobs"] == ["JOB_TARGET", "JOB_DEP"]
    assert summary["resultTables"] == ["DWS.TARGET", "DWS.DEP_TABLE"]
    assert summary["recvPlans"] == ["PLAN_A"]
    assert summary["outfiles"] == ["dep.out"]
    assert summary["stats"]["jobCount"] == 2


def test_lineage_metadata_queries_execute_once_per_context_load():
    calls = []

    def query(name, rows):
        def run():
            calls.append(name)
            return rows
        return run

    service = SimpleNamespace(
        list_job_outfiles=query("outfiles", [("JOB", "a.out")]),
        list_result_table_recv_details=query("recv_details", []),
        list_result_table_sys_names=query("sys_names", []),
        list_recv_mapping_plans=query("mapping_plans", []),
    )
    context = _load_lineage_metadata(SimpleNamespace(audit_metadata_service=service), None)

    assert calls == ["outfiles", "recv_details", "sys_names", "mapping_plans"]
    assert context["job_outfile_rows"] == [("JOB", "a.out")]


def test_lineage_metadata_failure_degrades_without_changing_payload_shape():
    class FailingService:
        def list_job_outfiles(self):
            raise RuntimeError("db unavailable")

        list_result_table_recv_details = list_job_outfiles
        list_result_table_sys_names = list_job_outfiles
        list_recv_mapping_plans = list_job_outfiles

    context = _load_lineage_metadata(SimpleNamespace(audit_metadata_service=FailingService()), None)
    summary = re_service.build_wide_table_lineage_summary(
        matched_rows=[],
        job_outfile_rows=context["job_outfile_rows"],
        result_table_recv_detail_rows=context["result_table_recv_detail_rows"],
        result_table_sys_name_rows=context["result_table_sys_name_rows"],
        recv_mapping_plan_rows=context["recv_mapping_plan_rows"],
    )

    assert len(context["warnings"]) == 4
    assert summary["stats"]["jobCount"] == 0
    assert "empty lineage metadata" in summary["warnings"]


def test_payload_reuses_context_without_requerying_metadata_or_remerging():
    row = _row("JOB_TARGET", "33:JOB_DEP", "/etl/DWS.TARGET/target.py")

    class UnexpectedQueryService:
        def __getattr__(self, name):
            raise AssertionError(f"unexpected metadata query: {name}")

    context = {
        "merge_df": pd.DataFrame([row]),
        "dependency_lookup": {"JOB_DEP": "DWS.DEP_TABLE"},
        "lineage_rows_by_path": {
            re_service.tail_path("/etl/DWS.TARGET/target.py", 4): [row],
        },
        "job_outfile_lookup": {"JOB_DEP": "dep.out"},
        "job_outfile_rows": [("JOB_DEP", "dep.out")],
        "result_table_recv_detail_rows": [("DWS.DEP_TABLE", "PLAN_A", "SYS_A")],
        "result_table_sys_name_rows": [],
        "recv_mapping_plan_rows": [],
    }
    modules = SimpleNamespace(
        re_service=re_service,
        audit_metadata_service=UnexpectedQueryService(),
    )

    summary = _build_lineage_summary_payload(
        modules,
        py_lists=["/etl/DWS.TARGET/target.py"],
        lineage_context=context,
    )

    assert summary["jobs"] == ["JOB_TARGET", "JOB_DEP"]
    assert summary["outfiles"] == ["dep.out"]
