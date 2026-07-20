from __future__ import annotations


def build_nups_report(
    *,
    task,
    svn,
    changes,
    conflicts,
    sql_checks,
    py_scripts,
    ai=None,
):
    report = {
        "task": task,
        "svn": svn,
        "changes": changes,
        "conflicts": conflicts,
        "sqlChecks": sql_checks,
        "pyScripts": py_scripts,
        "assetIssues": [],
        "unifiedAssetIssues": [],
    }
    if ai:
        report["ai"] = ai
    return report
