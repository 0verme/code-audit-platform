from __future__ import annotations

from ...core.runtime import WorkflowRuntimeContext
from ...shared.findings import CheckResult, finding_messages
from ...shared.report_helpers import build_source_file
from ...shared.result_normalizer import dedupe_tables
from .report import build_nups_report


def run_nups(context: WorkflowRuntimeContext) -> dict:
    mods = context.mods
    svn_result = context.source_payload
    exported = svn_result["exported_paths"]
    sql_lists, py_lists = mods.nups_rule.get_nups_type(exported)

    def source_file(path, section, kind):
        if callable(context.build_source_file):
            return context.build_source_file(path, section=section, kind=kind)
        return build_source_file(
            path,
            section=section,
            kind=kind,
            download_url=context.download_url,
            relative_path=mods.re_service.safe_remove_prefix,
        )

    source_files = [
        descriptor
        for path, section, kind in (
            *((path, "nups-sql", "sql") for path in (sql_lists or [])),
            *((path, "nups-py", "python") for path in (py_lists or [])),
        )
        if (descriptor := source_file(path, section, kind))
    ]

    context.update(progress=45, step="NUPS SQL 检查")
    sql_checks = []
    for path in sql_lists or []:
        result = context.safe("NUPS SQL 规则", lambda p=path: mods.nups_rule.rule_dws(p), CheckResult())
        sql_checks.append(
            {
                "script": mods.re_service.get_filename(path),
                "downloadUrl": context.download_url(path),
                "messages": finding_messages(result.findings),
            }
        )

    context.update(progress=65, step="NUPS 加工程序检查")
    py_scripts = []
    for path in py_lists or []:
        file_name = mods.re_service.get_filename(path)
        result = context.safe(
            f"NUPS 加工程序规则({file_name})",
            lambda p=path: mods.nups_rule.rule_dws_py(p),
            CheckResult(),
        )
        sql_tables = dedupe_tables(result.artifacts.get("sql_tables", []))
        table_name = context.safe("表名解析", lambda p=path: mods.nups_rule.get_program_table_name(p), "")
        py_scripts.append(
            {
                "script": file_name,
                "downloadUrl": context.download_url(path),
                "path": mods.re_service.safe_remove_prefix(path),
                "table": table_name,
                "messages": finding_messages(result.findings),
                "sqlRefs": sql_tables,
            }
        )

    all_rows = [{"level": msg["level"], "msg": msg["msg"]} for check in sql_checks for msg in check["messages"]]
    all_rows += [{"level": msg["level"], "msg": msg["msg"]} for script in py_scripts for msg in script["messages"]]
    errors = sum(1 for row in all_rows if row["level"] == "err")
    warnings = sum(1 for row in all_rows if row["level"] == "warn")
    ai = context.build_ai(py_lists or sql_lists or [], errors, warnings)
    conflicts = context.build_conflicts(svn_result)
    status = context.status_of(errors + len(conflicts), warnings)

    return build_nups_report(
        task=context.build_task_meta(
            svn_result,
            status,
            {
                "changedFiles": len(svn_result.get("branch_changed_files", [])),
                "checks": len(sql_lists or []) + len(py_lists or []),
                "errors": errors,
                "warnings": warnings,
                "conflicts": len(conflicts),
            },
        ),
        svn=context.build_svn_section(svn_result),
        changes=context.build_changes(svn_result),
        conflicts=conflicts,
        sql_checks=sql_checks,
        py_scripts=py_scripts,
        source_files=source_files,
        ai=ai,
    )
