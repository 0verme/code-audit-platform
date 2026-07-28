import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.shared.findings import CheckResult, Finding, finding_messages, finding_rows  # noqa: E402


def test_finding_validates_required_fields_and_level():
    with pytest.raises(ValueError, match="rule_code"):
        Finding("", "规则", "err", "说明")
    with pytest.raises(ValueError, match="unsupported finding level"):
        Finding("demo.rule", "规则", "fatal", "说明")


def test_finding_serializes_rule_code_and_preserves_existing_context():
    finding = Finding("demo.rule", "示例规则", "warn", "示例说明", file="source.sql")

    row = finding_rows([finding], file="fallback.sql")[0]

    assert row == {
        "ruleCode": "demo.rule",
        "rule": "示例规则",
        "level": "warn",
        "msg": "示例说明",
        "file": "source.sql",
    }


def test_check_result_supports_all_levels_and_derives_count():
    result = CheckResult()
    result.add("demo.error", "错误规则", "err", "错误")
    result.add("demo.warning", "警告规则", "warn", "警告")
    result.add("demo.info", "提示规则", "info", "提示")

    assert result.count == 3
    assert [item["level"] for item in finding_messages(result.findings)] == ["err", "warn", "info"]
