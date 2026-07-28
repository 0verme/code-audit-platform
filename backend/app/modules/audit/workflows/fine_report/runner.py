from __future__ import annotations

import os
from urllib.parse import quote
from app.config.audit_rules import get_audit_rules

from ...compat import build_legacy_fine_audit_result_rows
from ...core.runtime import WorkflowRuntimeContext
from ...shared.findings import CheckResult, finding_messages
from ...shared.result_normalizer import dedupe_tables, normalize_table
from ...shared.source_files import resolve_source_file
from ...shared.table_annotations import annotate_table, build_result_table_sys_name_map
from .report import build_fine_report


DEFAULT_FINE_REPORT_PREVIEW_URL = "https://fine.example.com/fine/svn_check.html"


def get_fine_report_preview_url() -> str:
    """Return the deployment-configured FineReport preview endpoint."""
    return os.getenv("FINE_REPORT_PREVIEW_URL", DEFAULT_FINE_REPORT_PREVIEW_URL).strip().rstrip("/")


def run_fine(context: WorkflowRuntimeContext) -> dict:
    mods = context.services.mods
    svn_result = context.source_payload
    exported = svn_result["exported_paths"]

    audit_rules = get_audit_rules()
    conventions = audit_rules["fine_report"]["file_conventions"]
    highlight_result_source_systems = set(
        audit_rules["display"].get("highlight_result_source_systems", [])
    )
    cpt_lists, menu_url, authority_url = [], "", ""
    for path in exported:
        if path.lower().endswith(tuple(conventions["template_extensions"])):
            cpt_lists.append(path)
        elif conventions["menu_filename"] in path:
            menu_url = path
        elif conventions["authority_filename"] in path:
            authority_url = path

    source_files = [
        descriptor
        for path, section, kind in (
            (menu_url, "menu", "menu"),
            (authority_url, "authority", "authority"),
            *((path, "reports", "template") for path in cpt_lists),
        )
        if (descriptor := resolve_source_file(context, path, section=section, kind=kind))
    ]

    context.progress.update(progress=40, step="目录与权限检查")
    menu_section = authority_section = None
    menu_lists = []
    if menu_url:
        table = context.services.safe(
            "目录表(menu.txt)",
            lambda: mods.re_service.load_txt_to_df(menu_url, ["后台目录", "前台目录", "预览方式"]),
            None,
        )
        result = context.services.safe("目录规则(rule_menu)", lambda: mods.fine_rule.rule_menu(menu_url), CheckResult())
        menu_lists = result.artifacts.get("menu_entries", [])
        menu_section = {
            "file": mods.re_service.get_filename(menu_url),
            "downloadUrl": context.services.download_url(menu_url),
            "columns": ["后台目录", "前台目录", "预览方式"],
            "rows": table.fillna("").astype(str).values.tolist() if table is not None else [],
            "messages": finding_messages(result.findings),
        }
    if authority_url:
        table = context.services.safe(
            "权限表(authority.txt)",
            lambda: mods.re_service.load_txt_to_df2(authority_url, ["前台目录", "赋予权限"]),
            None,
        )
        result = context.services.safe(
            "权限规则(rule_authority)",
            lambda: mods.fine_rule.rule_authority(authority_url, menu_lists),
            CheckResult(),
        )
        authority_section = {
            "file": mods.re_service.get_filename(authority_url),
            "downloadUrl": context.services.download_url(authority_url),
            "columns": ["前台目录", "赋予权限"],
            "rows": table.fillna("").astype(str).values.tolist() if table is not None else [],
            "messages": finding_messages(result.findings),
        }

    context.progress.update(progress=55, step="帆软模板检查")
    metadata_profile = context.services.get_active_profile_name()
    catalog_loader = getattr(mods, "load_result_table_catalog_snapshot", None)
    catalog = context.services.safe(
        "结果表登记库(lineage)",
        lambda: catalog_loader(profile=metadata_profile) if callable(catalog_loader) else None,
        None,
    )
    registered = set(
        catalog.registered
        if catalog is not None
        else context.services.safe(
            "结果表登记库(lineage)",
            lambda: mods.load_registered_result_tables(profile=metadata_profile),
            set(),
        )
    )
    para_tables = set(
        context.services.safe(
            "码值参数表(all_para_table_lists)",
            lambda: {normalize_table(row[0]) for row in mods.public_data.all_para_table_lists() if row and row[0]},
            set(),
        )
    )
    disabled, sys_name_map = context.services.safe(
        "结果表标注信息",
        lambda: (
            set(catalog.disabled) if catalog is not None else {
                normalize_table(row[0])
                for row in mods.public_data.all_disabled_result_tables()
                if row and row[0]
            },
            build_result_table_sys_name_map(
                mods.public_data.all_result_table_sys_names(),
                normalize_table=normalize_table,
            ),
        ),
        (set(), {}),
    )

    reports, all_ref_tables = [], []
    for path in cpt_lists:
        file_name = mods.re_service.get_filename(path)
        result = context.services.safe(f"帆软规则({file_name})", lambda p=path: mods.fine_rule.rule_fine(p), CheckResult())
        issues, ref_tables = [], []
        title, conn, engine_flag, sheets, datasets = file_name, "-", "", [], []
        viewlet = ""
        if isinstance(result, CheckResult):
            issues = [
                {
                    **finding.with_context(category="dataset", location=file_name).to_dict(),
                    "cat": finding.category or "dataset",
                    "loc": finding.location or file_name,
                }
                for finding in result.findings
            ]
            detail = result.artifacts
            viewlet = str(detail.get("viewlet") or "").replace("\\", "/")
            title = viewlet or file_name
            conn = str(detail.get("connection") or "-")
            engine_flag = str(detail.get("engine") or "")
            sheets = list(detail.get("sheets") or [])
            sql_tables = dedupe_tables(detail.get("sql_tables", []))
            sql_text = context.services.safe("数据集 SQL 提取", lambda p=path: mods.fine_rule.get_cpt_sql(p), "")
            if sql_text:
                datasets = [{"name": "数据集 SQL", "sql": (sql_text or "").strip(), "rows": "-"}]
            for name in sql_tables:
                table_type = "result" if name in registered else ("src" if name in para_tables else "mid")
                annotation = annotate_table(
                    name,
                    disabled,
                    sys_name_map,
                    normalize_table=normalize_table,
                    highlight_result_source_systems=highlight_result_source_systems,
                )
                ref_tables.append(
                    {
                        "type": table_type,
                        **annotation,
                    }
                )
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
                "downloadUrl": context.services.download_url(path),
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
    ai = context.services.build_ai(cpt_lists, errors, warnings)
    status = context.reports.status_of(errors, warnings)

    context.services.save_category_rows(build_legacy_fine_audit_result_rows(reports))

    return build_fine_report(
        task=context.reports.build_task_meta(
            svn_result,
            status,
            {
                "reports": len(reports),
                "checks": len(cpt_lists) + (1 if menu_url else 0) + (1 if authority_url else 0),
                "errors": errors,
                "warnings": warnings,
            },
        ),
        svn=context.reports.build_svn_section(svn_result),
        changes=context.reports.build_changes(svn_result),
        menu_section=menu_section,
        authority_section=authority_section,
        reports=reports,
        ref_tables=all_ref_tables,
        source_files=source_files,
        metadata_profile=metadata_profile,
        ai=ai,
    )
