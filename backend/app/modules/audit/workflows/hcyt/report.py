from __future__ import annotations

from ...shared.lineage_overlay import build_lineage_overlay


def build_hcyt_final_report(
    *,
    task,
    svn,
    changes,
    conflicts,
    grouped,
    sql_checks,
    config_files,
    schedule,
    py_scripts,
    ref_tables,
    deps,
    asset_issues,
    unified_asset_issues,
    lineage_summary,
    source_files=None,
    metadata_profile="",
    ai=None,
):
    report = {
        "task": task,
        "svn": svn,
        "changes": changes,
        "conflicts": conflicts,
        "dws": grouped["dws"],
        "hive": grouped["hive"],
        "python": grouped["python"],
        "sbin": grouped["sbin"],
        "config": grouped["config"],
        "recv": grouped["recv"],
        "sqlChecks": sql_checks,
        "configFiles": config_files,
        "schedule": schedule,
        "pyScripts": py_scripts,
        "refTables": ref_tables,
        "deps": deps,
        "assetIssues": asset_issues,
        "unifiedAssetIssues": unified_asset_issues,
        "lineageSummary": lineage_summary,
        "sourceFiles": list(source_files or []),
        "lineageOverlay": build_lineage_overlay(
            py_scripts,
            revision=task.get("revision", "") if isinstance(task, dict) else "",
            changes=changes,
        ),
    }
    if metadata_profile:
        report["metadataProfile"] = metadata_profile
    if ai:
        report["ai"] = ai
    return report


def build_hcyt_report(**kwargs):
    return build_hcyt_final_report(**kwargs)


def build_hcyt_partial_report(
    *,
    changes,
    conflicts,
    grouped,
    config_files,
    schedule,
    py_scripts,
    ref_tables,
    deps,
    asset_issues,
    unified_asset_issues,
    lineage_summary,
    source_files=None,
):
    return {
        "changes": changes,
        "conflicts": conflicts,
        "dws": grouped["dws"],
        "hive": grouped["hive"],
        "python": grouped["python"],
        "sbin": grouped["sbin"],
        "config": grouped["config"],
        "recv": grouped["recv"],
        "configFiles": config_files,
        "schedule": schedule,
        "pyScripts": py_scripts,
        "refTables": ref_tables,
        "deps": deps,
        "assetIssues": asset_issues,
        "unifiedAssetIssues": unified_asset_issues,
        "lineageSummary": lineage_summary,
        "sourceFiles": list(source_files or []),
        "lineageOverlay": build_lineage_overlay(py_scripts, changes=changes),
    }
