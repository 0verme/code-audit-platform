from __future__ import annotations


def build_fine_report(
    *,
    task,
    svn,
    menu_section,
    authority_section,
    reports,
    ref_tables,
    ai=None,
):
    report = {
        "task": task,
        "svn": svn,
        "menu": menu_section,
        "authority": authority_section,
        "reports": reports,
        "refTables": ref_tables,
        "assetIssues": [],
        "unifiedAssetIssues": [],
    }
    if ai:
        report["ai"] = ai
    return report
