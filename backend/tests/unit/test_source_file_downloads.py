from pathlib import Path

import pytest

from app.modules.audit.engine import TaskRun
from app.modules.audit.source.download import allowed_report_paths, resolve_source_download_path
from app.modules.audit.workflows.fine_report.report import build_fine_report
from app.modules.audit.workflows.hcyt.report import build_hcyt_report
from app.modules.audit.workflows.nups.report import build_nups_report


def test_source_files_extend_the_task_download_allowlist(tmp_path):
    source = tmp_path / "调度 空格" / "PROGRAM_001.xls"
    source.parent.mkdir()
    source.write_bytes(b"xls")
    relative = "调度 空格/PROGRAM_001.xls"
    report = {
        "changes": [{"path": "sql/dws.sql"}],
        "sourceFiles": [{"path": relative, "downloadUrl": "/download"}],
    }

    assert allowed_report_paths(report) == {"sql/dws.sql", relative}
    assert resolve_source_download_path(
        task={"source_type": "local", "source_ref": str(tmp_path)},
        report=report,
        relative_path=relative,
        export_base=tmp_path,
    ) == source.resolve()

    with pytest.raises(FileNotFoundError):
        resolve_source_download_path(
            task={"source_type": "local", "source_ref": str(tmp_path)},
            report=report,
            relative_path="secret.txt",
            export_base=tmp_path,
        )


def test_task_run_registers_audited_fallback_file_inside_download_root(tmp_path):
    source = tmp_path / "调度" / "CALE_001.xls"
    source.parent.mkdir()
    source.write_bytes(b"xls")
    run = TaskRun.__new__(TaskRun)
    run.task_id = 17
    run._source_download_root = tmp_path.resolve()
    run._source_download_paths = {}
    run._source_download_by_relative = {}

    assert run.download_url(source).endswith("path=%E8%B0%83%E5%BA%A6/CALE_001.xls")
    assert run._source_download_paths[str(source.resolve())] == "调度/CALE_001.xls"

    outside = tmp_path.parent / "outside.txt"
    outside.write_text("no", encoding="utf-8")
    assert run.download_url(outside) == ""


def test_all_workflow_reports_preserve_source_file_descriptors():
    descriptor = {
        "section": "config",
        "kind": "schema-config",
        "name": "配置.json",
        "path": "配置.json",
        "downloadUrl": "/download",
    }
    hcyt = build_hcyt_report(
        task={},
        svn={},
        changes=[],
        conflicts=[],
        grouped={key: [] for key in ("dws", "hive", "python", "sbin", "config", "recv")},
        sql_checks={},
        config_files=[],
        schedule={},
        py_scripts=[],
        ref_tables=[],
        deps=[],
        asset_issues=[],
        unified_asset_issues=[],
        lineage_summary={},
        source_files=[descriptor],
    )
    fine = build_fine_report(
        task={},
        svn={},
        changes=[],
        menu_section=None,
        authority_section=None,
        reports=[],
        ref_tables=[],
        source_files=[descriptor],
    )
    nups = build_nups_report(
        task={},
        svn={},
        changes=[],
        conflicts=[],
        sql_checks=[],
        py_scripts=[],
        source_files=[descriptor],
    )

    assert hcyt["sourceFiles"] == [descriptor]
    assert fine["sourceFiles"] == [descriptor]
    assert nups["sourceFiles"] == [descriptor]
