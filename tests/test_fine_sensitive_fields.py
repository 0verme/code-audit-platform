import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.workflows.fine_report import checks as fine_rule  # noqa: E402


def _audit_rules(sensitive_field_rules=None):
    return {
        "fine_report": {
            "sensitive_field_rules": sensitive_field_rules or {},
        }
    }


def test_default_sensitive_fields_are_split_by_severity(monkeypatch):
    monkeypatch.setattr(fine_rule, "get_audit_rules", lambda: _audit_rules())

    error_fields, warning_fields = fine_rule.find_sensitive_fields(
        "SELECT CERT_NO, ADDRESS, MOBILE, LANDLINE, CERT_TYPE, CARD_NO, ACCT_NO, EMAIL"
    )

    assert [item.split("(", 1)[0] for item in error_fields] == ["身份证", "地址", "手机号", "座机"]
    assert [item.split("(", 1)[0] for item in warning_fields] == ["证件类型", "卡号", "账号", "邮箱"]


def test_configured_sensitive_fields_keep_name_based_severity(monkeypatch):
    configured_rules = {
        "身份证": ["CUSTOM_ID"],
        "自定义字段": ["CUSTOM_FIELD"],
    }
    monkeypatch.setattr(
        fine_rule,
        "get_audit_rules",
        lambda: _audit_rules(configured_rules),
    )

    error_fields, warning_fields = fine_rule.find_sensitive_fields(
        "SELECT CUSTOM_ID, CUSTOM_FIELD"
    )

    assert error_fields == ["身份证(命中关键字: CUSTOM_ID)"]
    assert warning_fields == ["自定义字段(命中关键字: CUSTOM_FIELD)"]


def test_rule_fine_emits_separate_error_and_warning_findings(monkeypatch):
    monkeypatch.setattr(fine_rule, "get_audit_rules", lambda: _audit_rules())
    monkeypatch.setattr(fine_rule, "read_data_from_file", lambda _path: "")
    monkeypatch.setattr(fine_rule, "get_cpt_yuan", lambda _path: "")
    monkeypatch.setattr(fine_rule, "find_report", lambda _path: [])
    monkeypatch.setattr(
        fine_rule,
        "get_cpt_sql",
        lambda _path: "SELECT CERT_NO, CARD_NO FROM DWP.CUSTOMER",
    )
    monkeypatch.setattr(fine_rule, "find_clientPaging", lambda _path: "")
    monkeypatch.setattr(fine_rule, "find_hardcoded_dates", lambda _text: [])
    monkeypatch.setattr(fine_rule, "extract_tables", lambda _text: [])
    monkeypatch.setattr(fine_rule, "find_dot_strings", lambda _text: [])

    result = fine_rule.rule_fine("[FR001]客户报表.cpt")
    sensitive_findings = [
        finding
        for finding in result.findings
        if finding.rule_code == "fine.report.sensitive_fields"
    ]

    assert [finding.level for finding in sensitive_findings] == ["err", "warn"]
    assert "身份证(命中关键字: CERT_NO)" in sensitive_findings[0].msg
    assert "卡号(命中关键字: CARD_NO)" in sensitive_findings[1].msg
