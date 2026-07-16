from __future__ import annotations

import os
from urllib.parse import quote
from app.config.audit_rules import get_audit_rules

from .compat import build_legacy_fine_audit_result_rows
from .fine_report_builder import build_fine_report
from .result_normalizer import dedupe_tables, normalize_table, rule_label, text_to_messages
from .workflow_runtime import WorkflowRuntimeContext


DEFAULT_FINE_REPORT_PREVIEW_URL = "https://fine.example.com/svn_check.html"


def get_fine_report_preview_url() -> str:
    """Return the deployment-configured FineReport preview endpoint."""
    return os.getenv("FINE_REPORT_PREVIEW_URL", DEFAULT_FINE_REPORT_PREVIEW_URL).strip().rstrip("/")


def run_fine(context: WorkflowRuntimeContext) -> dict:
    mods = context.mods
    svn_result = context.source_payload
    exported = svn_result["exported_paths"]

    conventions = get_audit_rules()["fine_report"]["file_conventions"]
    cpt_lists, menu_url, authority_url = [], "", ""
    for path in exported:
        if path.lower().endswith(tuple(conventions["template_extensions"])):
            cpt_lists.append(path)
        elif conventions["menu_filename"] in path:
            menu_url = path
        elif conventions["authority_filename"] in path:
            authority_url = path

    context.update(progress=40, step="目录与权限检查")
    menu_section = authority_section = None
    menu_lists = []
    if menu_url:
        table = context.safe(
            "目录表(menu.txt)",
            lambda: mods.re_service.load_txt_to_df(menu_url, ["后台目录", "前台目录", "预览方式"]),
            None,
        )
        result = context.safe("目录规则(rule_menu)", lambda: mods.fine_rule.rule_menu(menu_url), ([], "", 0))
        menu_lists = result[0] if isinstance(result, tuple) and result else []
        menu_section = {
            "columns": ["后台目录", "前台目录", "预览方式"],
            "rows": table.fillna("").astype(str).values.tolist() if table is not None else [],
            "messages": text_to_messages(result[1] if isinstance(result, tuple) and len(result) > 1 else "", ""),
        }
    if authority_url:
        table = context.safe(
            "权限表(authority.txt)",
            lambda: mods.re_service.load_txt_to_df2(authority_url, ["前台目录", "赋予权限"]),
            None,
        )
        result = context.safe(
            "权限规则(rule_authority)",
            lambda: mods.fine_rule.rule_authority(authority_url, menu_lists),
            ("", 0),
        )
        text = result[0] if isinstance(result, tuple) else str(result)
        authority_section = {
            "columns": ["前台目录", "赋予权限"],
            "rows": table.fillna("").astype(str).values.tolist() if table is not None else [],
            "messages": text_to_messages(text, ""),
        }

    context.update(progress=55, step="帆软模板检查")
    registered = set(
        context.safe(
            "结果表登记库(lineage)",
            lambda: mods.load_registered_result_tables(profile=context.get_active_profile_name()),
            set(),
        )
    )
    para_tables = set(
        context.safe(
            "码值参数表(all_para_table_lists)",
            lambda: {normalize_table(row[0]) for row in mods.public_data.all_para_table_lists() if row and row[0]},
            set(),
        )
    )
    disabled, sys_name_map = context.safe(
        "结果表标注信息",
        lambda: (
            {
                normalize_table(row[0])
                for row in mods.public_data.all_disabled_result_tables()
                if row and row[0]
            },
            {
                normalize_table(row[0]): str(row[1])
                for row in mods.public_data.all_result_table_sys_names()
                if row and row[0]
            },
        ),
        (set(), {}),
    )

    reports, all_ref_tables = [], []
    for path in cpt_lists:
        file_name = mods.re_service.get_filename(path)
        result = context.safe(f"帆软规则({file_name})", lambda p=path: mods.fine_rule.rule_fine(p), None)
        issues, ref_tables = [], []
        title, conn, engine_flag, sheets, datasets = file_name, "-", "", [], []
        viewlet = ""
        if isinstance(result, tuple) and len(result) >= 3:
            text, _cnt, detail = result[0], result[1], result[2]
            issues = [
                {"cat": "dataset", "loc": file_name, "rule": rule_label(line), "level": "err", "msg": line}
                for line in str(text or "").split("\n")
                if line.strip() and line.strip() != "存在问题:"
            ]
            viewlet = str(detail[0]) if detail and detail[0] else ""
            title = viewlet or file_name
            conn = str(detail[1]) if len(detail) > 1 and detail[1] else "-"
            engine_flag = str(detail[2]) if len(detail) > 2 else ""
            sheets = list(detail[3]) if len(detail) > 3 and detail[3] else []
            sql_tables = dedupe_tables(detail[4] if len(detail) > 4 else [])
            sql_text = context.safe("数据集 SQL 提取", lambda p=path: mods.fine_rule.get_cpt_sql(p), "")
            if sql_text:
                datasets = [{"name": "数据集 SQL", "sql": (sql_text or "").strip(), "rows": "-"}]
            for name in sql_tables:
                table_type = "result" if name in registered else ("src" if name in para_tables else "mid")
                ref_tables.append(
                    {
                        "name": name,
                        "type": table_type,
                        "disabled": name in disabled,
                        "sysNames": [sys_name_map[name]] if name in sys_name_map else [],
                        "highlight": (name in disabled) or (name in sys_name_map),
                    }
                )
        elif result is not None:
            issues = [{"cat": "tpl", "loc": file_name, "rule": "规则执行异常", "level": "warn", "msg": str(result)}]

        preview_url = f"{get_fine_report_preview_url()}?viewlet={quote(viewlet, safe='')}" if viewlet else ""
        reports.append(
            {
                "title": title,
                "file": mods.re_service.safe_remove_prefix(path),
                "type": "frm" if path.endswith(".frm") else "cpt",
                "change": "M",
                "conn": conn,
                "engine": engine_flag,
                "sheets": sheets,
                "previewUrl": preview_url,
                "downloadUrl": context.download_url(path),
                "focus": "重点检查数据集 SQL、数据连接、敏感字段与权限。",
                "datasets": datasets,
                "issues": issues,
                "refTables": ref_tables,
            }
        )
        seen = {item["name"] for item in all_ref_tables}
        for item in ref_tables:
            if item["name"] not in seen:
                all_ref_tables.append(item)
                seen.add(item["name"])

    errors = sum(1 for report in reports for issue in report["issues"] if issue["level"] == "err")
    errors += sum(
        1
        for section in (menu_section, authority_section)
        if section
        for msg in section["messages"]
        if msg["level"] == "err"
    )
    warnings = sum(1 for report in reports for issue in report["issues"] if issue["level"] == "warn")
    warnings += sum(
        1
        for section in (menu_section, authority_section)
        if section
        for msg in section["messages"]
        if msg["level"] == "warn"
    )
    ai = context.build_ai(cpt_lists, errors, warnings)
    status = context.status_of(errors, warnings)

    context.save_category_rows(build_legacy_fine_audit_result_rows(reports))

    return build_fine_report(
        task=context.build_task_meta(
            svn_result,
            status,
            {
                "reports": len(reports),
                "checks": len(cpt_lists) + (1 if menu_url else 0) + (1 if authority_url else 0),
                "errors": errors,
                "warnings": warnings,
            },
        ),
        svn=context.build_svn_section(svn_result),
        menu_section=menu_section,
        authority_section=authority_section,
        reports=reports,
        ref_tables=all_ref_tables,
        ai=ai,
    )
