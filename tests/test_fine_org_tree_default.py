import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.workflows.fine_report import checks as fine_rule  # noqa: E402


@pytest.mark.parametrize(
    "sql",
    [
        "select min(t.nbjgh) from dwp.P_SYS_USER_INFO t where t.gh='${fine_username}'",
        "SELECT MIN(T.NBJGH)  FROM DWP.P_SYS_USER_INFO T WHERE T.GH ='${FINE_USERNAME}'",
        (
            "SeLeCt\tMiN ( T . NbJgH )\n"
            "FrOm Dwp . P_Sys_User_Info\tT\n"
            "WhErE T . Gh = '${Fine_Username}'"
        ),
    ],
)
def test_org_tree_default_sql_accepts_formatting_differences(sql):
    assert fine_rule.has_valid_org_tree_default_sql(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "select min(t.wrong_column) from dwp.p_sys_user_info t where t.gh='${fine_username}'",
        "select min(t.nbjgh) from dwp.wrong_table t where t.gh='${fine_username}'",
        "select min(u.nbjgh) from dwp.p_sys_user_info u where u.gh='${fine_username}'",
        "select min(t.nbjgh) from dwp.p_sys_user_info t where t.gh='${wrong_parameter}'",
    ],
)
def test_org_tree_default_sql_rejects_business_rule_changes(sql):
    assert not fine_rule.has_valid_org_tree_default_sql(sql)


def _stub_rule_fine_dependencies(monkeypatch, data):
    monkeypatch.setattr(fine_rule, "read_data_from_file", lambda _path: data)
    monkeypatch.setattr(fine_rule, "get_cpt_yuan", lambda _path: "")
    monkeypatch.setattr(fine_rule, "find_report", lambda _path: [])
    monkeypatch.setattr(fine_rule, "get_cpt_sql", lambda _path: "")
    monkeypatch.setattr(fine_rule, "find_clientPaging", lambda _path: "")
    monkeypatch.setattr(fine_rule, "find_hardcoded_dates", lambda _text: [])
    monkeypatch.setattr(fine_rule, "extract_tables", lambda _text: [])
    monkeypatch.setattr(fine_rule, "find_dot_strings", lambda _text: [])


def _org_tree_findings(result):
    return [
        finding
        for finding in result.findings
        if finding.rule_code == "fine.report.org_tree_default"
    ]


def test_rule_fine_does_not_report_formatted_valid_org_tree_sql(monkeypatch):
    _stub_rule_fine_dependencies(
        monkeypatch,
        (
            "权限机构树\n"
            "select min(t.nbjgh) from dwp.P_SYS_USER_INFO t "
            "where t.gh='${fine_username}'"
        ),
    )

    result = fine_rule.rule_fine("[FR001]机构树报表.cpt")

    assert _org_tree_findings(result) == []


def test_rule_fine_still_reports_invalid_org_tree_sql(monkeypatch):
    _stub_rule_fine_dependencies(
        monkeypatch,
        (
            "权限机构树\n"
            "select min(t.nbjgh) from dwp.P_SYS_USER_INFO t "
            "where t.gh='${wrong_parameter}'"
        ),
    )

    result = fine_rule.rule_fine("[FR001]机构树报表.cpt")

    findings = _org_tree_findings(result)
    assert len(findings) == 1
    assert findings[0].level == "err"
    assert findings[0].msg == "机构树默认值不对"
