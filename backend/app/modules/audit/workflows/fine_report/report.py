from __future__ import annotations


def build_fine_report(
    *,
    task,
    svn,
    changes,
    menu_section,
    authority_section,
    reports,
    ref_tables,
    metadata_profile="",
    ai=None,
):
    report = {
        "task": task,
        "svn": svn,
        "changes": changes,
        "menu": menu_section,
        "authority": authority_section,
        "reports": reports,
        "refTables": ref_tables,
        "assetIssues": [],
        "unifiedAssetIssues": [],
    }
    if metadata_profile:
        report["metadataProfile"] = metadata_profile
    if ai:
        report["ai"] = ai
    return report
