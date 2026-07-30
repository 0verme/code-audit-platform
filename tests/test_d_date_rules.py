import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.shared.d_date_rules import detect_d_date_issues  # noqa: E402
from app.modules.audit.workflows.hcyt.checks import python_rule as hcyt_rule  # noqa: E402
from app.modules.audit.workflows.nups import checks as nups_rule  # noqa: E402


ALL_D_DATE_ISSUES = {
    "d_date_to_date",
    "d_date_literal",
    "d_date_function",
    "to_date_d_date",
    "d_date_less_than",
    "d_date_greater_than",
}


def _rule_codes(result):
    return {finding.rule_code for finding in result.findings}


def test_detect_d_date_issues_matches_complete_qualified_identifiers():
    sql = """
    t.d_date = to_date('20240101', 'YYYYMMDD')
    OR D_DATE = DATE '2024-01-02'
    OR date(
        src.d_date
    ) = DATE '2024-01-03'
    OR to_date(src.D_DATE, 'YYYYMMDD') = DATE '2024-01-04'
    OR t.d_date
        <= '20241231'
    OR T.D_DATE\t>= '20240101'
    """

    assert detect_d_date_issues(sql) == ALL_D_DATE_ISSUES


def test_detect_d_date_issues_ignores_identifiers_containing_d_date():
    sql = """
    t.kod_date = to_date('20240101', 'YYYYMMDD')
    OR end_date = DATE '2024-01-02'
    OR date(business_d_date) = DATE '2024-01-03'
    OR to_date(kod_date, 'YYYYMMDD') = DATE '2024-01-04'
    OR end_date <= '20241231'
    OR t.kod_date >= '20240101'
    """

    assert detect_d_date_issues(sql) == set()


@pytest.mark.parametrize(
    ("module", "prefix", "path"),
    [
        (nups_rule, "nups", "C:/repo/DWS_DM.TABLE_A/program.py"),
        (hcyt_rule, "hcyt", "C:/repo/DWS_DM.TABLE_A/program.py"),
    ],
)
def test_program_rules_do_not_report_d_date_issues_for_kod_date(
    monkeypatch,
    module,
    prefix,
    path,
):
    source = """
    SQL = '''
    SELECT *
    FROM DWM.M_DEMO_SOURCE t
    WHERE t.kod_date >= '20240103'
      AND t.end_date <= '20241231'
      AND date(t.business_d_date) = DATE '2024-01-03'
      AND to_date(t.kod_date, 'YYYYMMDD') = DATE '2024-01-04'
    '''
    """
    monkeypatch.setattr(module, "read_data_from_file", lambda _path: source)
    monkeypatch.setattr(module, "all_sstb", lambda: [])
    monkeypatch.setattr(module, "all_view_names", lambda: [])
    monkeypatch.setattr(module, "all_function_names", lambda: [])
    monkeypatch.setattr(module, "all_tab_partitions", lambda _table: [])
    monkeypatch.setattr(module, "run_dws_ddl_rules", lambda _text: [])

    codes = _rule_codes(module.rule_dws_py(path))

    assert not {
        f"{prefix}.program.{issue}"
        for issue in ALL_D_DATE_ISSUES
    } & codes


@pytest.mark.parametrize(
    ("module", "prefix", "path"),
    [
        (nups_rule, "nups", "C:/repo/DWS_DM.TABLE_A/program.py"),
        (hcyt_rule, "hcyt", "C:/repo/DWS_DM.TABLE_A/program.py"),
    ],
)
def test_program_rules_keep_reporting_real_d_date_issues(
    monkeypatch,
    module,
    prefix,
    path,
):
    source = """
    SQL = '''
    SELECT *
    FROM DWM.M_DEMO_SOURCE t
    WHERE t.d_date = to_date('20240101', 'YYYYMMDD')
       OR t.d_date = DATE '2024-01-02'
       OR date(t.d_date) = DATE '2024-01-03'
       OR to_date(t.d_date, 'YYYYMMDD') = DATE '2024-01-04'
       OR t.d_date <= '20241231'
       OR t.d_date >= '20240101'
    '''
    """
    monkeypatch.setattr(module, "read_data_from_file", lambda _path: source)
    monkeypatch.setattr(module, "all_sstb", lambda: [])
    monkeypatch.setattr(module, "all_view_names", lambda: [])
    monkeypatch.setattr(module, "all_function_names", lambda: [])
    monkeypatch.setattr(module, "all_tab_partitions", lambda _table: [])
    monkeypatch.setattr(module, "run_dws_ddl_rules", lambda _text: [])

    codes = _rule_codes(module.rule_dws_py(path))

    assert {
        f"{prefix}.program.{issue}"
        for issue in ALL_D_DATE_ISSUES
    } <= codes
