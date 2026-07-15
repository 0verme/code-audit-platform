from __future__ import annotations


def build_hcyt_progress_payload(**sections):
    return [(key, value) for key, value in sections.items()]


def build_source_classified_progress(*, changes, conflicts):
    return build_hcyt_progress_payload(changes=changes, conflicts=conflicts)


def build_program_checked_progress(*, python_rows, py_scripts, ref_tables, deps):
    return build_hcyt_progress_payload(
        python=python_rows,
        pyScripts=py_scripts,
        refTables=ref_tables,
        deps=deps,
    )


def build_lineage_checked_progress(*, asset_issues, unified_asset_issues, lineage_summary):
    return build_hcyt_progress_payload(
        assetIssues=asset_issues,
        unifiedAssetIssues=unified_asset_issues,
        lineageSummary=lineage_summary,
    )


def publish_hcyt_progress(set_partial, events):
    for key, value in events:
        set_partial(key, value)
