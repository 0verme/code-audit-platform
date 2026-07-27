import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.workflows.fine_report import checks as fine_rule  # noqa: E402
from app.modules.audit.workflows.nups import checks as nups_rule  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _rule_codes(result):
    return {finding.rule_code for finding in result.findings}


def test_nups_local_workspace_covers_deterministic_rules(monkeypatch):
    workspace = ROOT / "test-NUPS" / "local-nups-workspace"
    files = [str(path) for path in workspace.rglob("*") if path.is_file()]
    sql_files, py_files = nups_rule.get_nups_type(files)

    assert {Path(path).name for path in sql_files} == {"cbrc.sql", "pboc.sql"}
    assert {Path(path).name for path in py_files} == {"001_bad_nups.py", "002_good_nups.py"}

    for name in ("all_sstb", "all_view_names", "all_function_names", "all_tab_partitions"):
        monkeypatch.setattr(nups_rule, name, lambda *args: [])

    sql_results = {Path(path).name: nups_rule.rule_dws(path) for path in sql_files}
    assert sql_results["cbrc.sql"].findings == []
    assert {
        "nups.sql.create_view",
        "nups.sql.create_function",
        "nups.sql.alter_statement",
        "nups.sql.dwm_operation",
        "nups.sql.legacy_group_clause",
        "nups.sql.legacy_marker",
        "nups.sql.protected_code_table",
        "nups.ddl.table_name",
        "nups.ddl.temp_table_name",
        "nups.ddl.column_comment",
    } <= _rule_codes(sql_results["pboc.sql"])

    py_results = {Path(path).name: nups_rule.rule_dws_py(path) for path in py_files}
    assert py_results["002_good_nups.py"].findings == []
    assert {
        "nups.program.create_view",
        "nups.program.create_function",
        "nups.program.for_loop",
        "nups.program.character_varying_length",
        "nups.program.varchar2_length",
        "nups.program.nested_nvl",
        "nups.program.nested_coalesce",
        "nups.program.distinct_review",
        "nups.program.legacy_outer_join",
        "nups.program.affected_rows_log",
        "nups.program.legacy_group_clause",
        "nups.program.hardcoded_date",
        "nups.program.missing_schema",
        "nups.program.scalar_subquery",
        "nups.program.in_subquery",
        "nups.program.end_dt_range",
        "nups.program.d_date_to_date",
        "nups.program.d_date_literal",
        "nups.program.d_date_function",
        "nups.program.to_date_d_date",
        "nups.program.d_date_less_than",
        "nups.program.d_date_greater_than",
    } <= _rule_codes(py_results["001_bad_nups.py"])
    assert nups_rule.get_program_table_name(
        next(path for path in py_files if path.endswith("001_bad_nups.py"))
    ) == "DWM.BAD_NUPS_RESULT"


def test_fine_report_local_workspace_covers_deterministic_rules(monkeypatch):
    workspace = ROOT / "test-fine-report" / "local-fine-report-workspace"
    monkeypatch.setattr(fine_rule, "all_role", lambda: [])
    monkeypatch.setattr(fine_rule, "all_fine", lambda: [])

    menu_result = fine_rule.rule_menu(str(workspace / "menu.txt"))
    assert {
        "fine.menu.root_prefix",
        "fine.menu.backend_extension",
        "fine.menu.backend_department_brackets",
        "fine.menu.backend_department",
        "fine.menu.backend_space",
        "fine.menu.frontend_root_prefix",
        "fine.menu.frontend_department",
        "fine.menu.frontend_finance_department",
        "fine.menu.frontend_department_brackets",
        "fine.menu.frontend_extension",
        "fine.menu.frontend_space",
    } <= _rule_codes(menu_result)
    assert "fine.menu.execution_error" not in _rule_codes(menu_result)

    authority_result = fine_rule.rule_authority(
        str(workspace / "authority.txt"),
        menu_result.artifacts["menu_entries"],
    )
    assert {"fine.authority.missing_menu", "fine.authority.missing_role"} <= _rule_codes(authority_result)

    report_results = {
        path.name: fine_rule.rule_fine(str(path))
        for path in [*workspace.rglob("*.cpt"), *workspace.rglob("*.frm")]
    }
    assert report_results["[FR001]合规报表.cpt"].findings == []
    assert _rule_codes(report_results["[FR002]空格 报表.frm"]) == {"fine.report.name_space"}
    assert {
        "fine.report.group_only",
        "fine.report.missing_number",
        "fine.report.org_tree_default",
        "fine.report.sensitive_fields",
    } <= _rule_codes(report_results["RPT_DEMO_CUSTOMER.frm"])
    assert {
        "fine.report.d_date_literal",
        "fine.report.d_date_to_date",
        "fine.report.distinct_review",
        "fine.report.end_dt_range",
        "fine.report.hardcoded_date",
        "fine.report.in_subquery",
        "fine.report.missing_number",
        "fine.report.missing_schema",
        "fine.report.scalar_subquery",
    } <= _rule_codes(report_results["RPT_DEMO_SALES.cpt"])
