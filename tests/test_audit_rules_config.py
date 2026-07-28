import copy
from pathlib import Path

import pytest
import yaml

from app.config.audit_rules import (
    AuditRulesConfigError,
    _config_path,
    get_audit_rules,
    load_audit_rules,
    refresh_audit_rules,
)
from app.modules.audit.source.resolver import classify_change


CANONICAL_RULES_PATH = Path(__file__).resolve().parents[1] / "backend" / "configs" / "audit_rules.yaml"


def _canonical_rules() -> dict:
    return copy.deepcopy(load_audit_rules(path=CANONICAL_RULES_PATH))


def _write_rules(tmp_path: Path, rules: dict, name: str = "rules.yaml") -> Path:
    rules_file = tmp_path / name
    rules_file.write_text(
        yaml.safe_dump(rules, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return rules_file


def test_default_config_path_targets_tracked_backend_config(monkeypatch):
    monkeypatch.delenv("AUDIT_RULES_CONFIG", raising=False)
    assert _config_path() == CANONICAL_RULES_PATH


def test_repository_rules_file_is_complete_and_valid():
    rules = load_audit_rules(path=CANONICAL_RULES_PATH)

    assert rules["schema_version"] == 1
    assert rules["hcyt"]["schedule"]["allowed_domains"]
    assert rules["audit_input"]["file_categories"]
    assert set(rules["hcyt"]["schedule"]["plan_name_rules"]) == {"DWD", "DWP", "DWM"}
    assert set(rules["hcyt"]["schedule"]["sequence_name_rules"]) == {"DWD", "DWP", "DWM"}
    assert {item["id"] for item in rules["workflows"]["definitions"]} == {
        "hcyt",
        "nups",
        "fine-report",
    }


def test_complete_alternate_rules_file_replaces_declared_values(tmp_path: Path):
    rules = _canonical_rules()
    rules["display"]["highlight_result_source_systems"] = ["CRM"]
    rules["hcyt"]["schedule"]["allowed_domains"] = ["DOMAIN_A"]

    loaded = load_audit_rules(path=_write_rules(tmp_path, rules))

    assert loaded["display"]["highlight_result_source_systems"] == ["CRM"]
    assert loaded["hcyt"]["schedule"]["allowed_domains"] == ["DOMAIN_A"]


def test_explicit_empty_lists_remain_empty(tmp_path: Path):
    rules = _canonical_rules()
    rules["hcyt"]["schedule"]["allowed_domains"] = []
    rules["audit_input"]["file_categories"] = []

    loaded = load_audit_rules(path=_write_rules(tmp_path, rules))

    assert loaded["hcyt"]["schedule"]["allowed_domains"] == []
    assert loaded["audit_input"]["file_categories"] == []


def test_classify_change_uses_configured_categories():
    refresh_audit_rules(path=CANONICAL_RULES_PATH)
    expected_categories = {
        "etl/dws.sql": "DWS SQL",
        "etl/hive.sql": "Hive SQL",
        "sql/demo.sql": "SQL",
        "scripts/job.py": "Python",
        "scripts/run.sh": "后置脚本",
        "schedule/jobs.xls": "调度表",
        "config/task.json": "配置文件",
        "report/demo.cpt": "报表模板",
        "report/menu.txt": "目录/权限",
        "docs/readme.md": "其他",
    }

    assert {path: classify_change(path) for path in expected_categories} == expected_categories


def test_missing_rules_file_reports_absolute_path(tmp_path: Path):
    missing = (tmp_path / "missing.yaml").resolve()

    with pytest.raises(AuditRulesConfigError, match="file does not exist") as exc_info:
        load_audit_rules(path=missing)

    assert str(missing) in str(exc_info.value)


def test_yaml_syntax_error_reports_line_and_file(tmp_path: Path):
    broken = tmp_path / "broken.yaml"
    broken.write_text("display: [unterminated\n", encoding="utf-8")

    with pytest.raises(AuditRulesConfigError, match=r"line \d+, column \d+") as exc_info:
        load_audit_rules(path=broken)

    assert str(broken.resolve()) in str(exc_info.value)


@pytest.mark.parametrize(
    ("mutate", "expected_path"),
    [
        (lambda rules: rules.update({"unexpected": {}}), "root.unexpected"),
        (lambda rules: rules["hcyt"]["schedule"].pop("allowed_domains"), "hcyt.schedule.allowed_domains"),
        (
            lambda rules: rules["hcyt"]["schedule"].update({"allowed_domains": "EDWS_DOMAIN"}),
            "hcyt.schedule.allowed_domains",
        ),
        (lambda rules: rules.update({"schema_version": 999}), "schema_version"),
    ],
)
def test_invalid_complete_config_reports_field_path(tmp_path: Path, mutate, expected_path: str):
    rules = _canonical_rules()
    mutate(rules)

    with pytest.raises(AuditRulesConfigError) as exc_info:
        load_audit_rules(path=_write_rules(tmp_path, rules))

    assert expected_path in str(exc_info.value)


def test_refresh_failure_preserves_last_valid_cache(tmp_path: Path):
    expected = refresh_audit_rules(path=CANONICAL_RULES_PATH)
    broken = tmp_path / "broken.yaml"
    broken.write_text("schema_version: 1\n", encoding="utf-8")

    with pytest.raises(AuditRulesConfigError):
        refresh_audit_rules(path=broken)

    assert get_audit_rules() == expected


def test_environment_override_requires_a_complete_file(monkeypatch, tmp_path: Path):
    partial = tmp_path / "partial.yaml"
    partial.write_text("schema_version: 1\n", encoding="utf-8")
    monkeypatch.setenv("AUDIT_RULES_CONFIG", str(partial))

    with pytest.raises(AuditRulesConfigError, match="root.audit_input"):
        load_audit_rules(path=_config_path())


def test_app_factory_validates_rules_before_startup(monkeypatch):
    import app

    error = AuditRulesConfigError("invalid rules for startup")

    def fail_validation():
        raise error

    monkeypatch.setattr(app, "get_audit_rules", fail_validation)

    with pytest.raises(AuditRulesConfigError) as exc_info:
        app.create_app()

    assert exc_info.value is error
