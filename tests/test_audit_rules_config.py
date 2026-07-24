from pathlib import Path

from app.config.audit_rules import DEFAULT_RULES, _config_path, load_audit_rules, refresh_audit_rules
from app.modules.audit.source.resolver import classify_change


def test_default_config_path_targets_backend_configs(monkeypatch):
    monkeypatch.delenv("AUDIT_RULES_CONFIG", raising=False)
    expected = Path(__file__).resolve().parents[1] / "backend" / "configs" / "audit_rules.yaml"
    assert _config_path() == expected


def test_valid_rules_file_overrides_declared_values(tmp_path: Path):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        "display:\n  highlight_result_source_systems: [CRM]\nhcyt:\n  schedule:\n    allowed_domains: [DOMAIN_A]\n",
        encoding="utf-8",
    )
    rules = load_audit_rules(path=rules_file)
    assert rules["display"]["highlight_result_source_systems"] == ["CRM"]
    assert rules["hcyt"]["schedule"]["allowed_domains"] == ["DOMAIN_A"]


def test_description_validation_rules_can_be_overridden(tmp_path: Path):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        "hcyt:\n"
        "  schedule:\n"
        "    description_validation:\n"
        "      min_meaningful_chinese_chars: 4\n"
        "      noise_phrases: [自定义模板]\n"
        "      invalid_values: [自定义占位]\n",
        encoding="utf-8",
    )

    rules = load_audit_rules(path=rules_file)
    description_rules = rules["hcyt"]["schedule"]["description_validation"]

    assert description_rules["min_meaningful_chinese_chars"] == 4
    assert description_rules["noise_phrases"] == ["自定义模板"]
    assert description_rules["invalid_values"] == ["自定义占位"]


def test_empty_allowed_domains_keeps_compatibility_defaults(tmp_path: Path):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        "display:\n  highlight_result_source_systems: []\nhcyt:\n  schedule:\n    allowed_domains: []\n",
        encoding="utf-8",
    )

    rules = load_audit_rules(path=rules_file)

    assert rules["hcyt"]["schedule"]["allowed_domains"] == DEFAULT_RULES["hcyt"]["schedule"]["allowed_domains"]
    assert rules["display"]["highlight_result_source_systems"] == []


def test_empty_file_categories_keeps_builtin_classification_map(tmp_path: Path):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        "audit_input:\n  file_categories: []\n",
        encoding="utf-8",
    )

    rules = load_audit_rules(path=rules_file)

    assert rules["audit_input"]["file_categories"] == DEFAULT_RULES["audit_input"]["file_categories"]


def test_non_empty_file_categories_override_builtin_classification_map(tmp_path: Path):
    rules_file = tmp_path / "rules.yaml"
    custom_categories = [{"suffixes": [".custom"], "category": "自定义"}]
    rules_file.write_text(
        "audit_input:\n"
        "  file_categories:\n"
        "    - suffixes: [.custom]\n"
        "      category: 自定义\n",
        encoding="utf-8",
    )

    rules = load_audit_rules(path=rules_file)

    assert rules["audit_input"]["file_categories"] == custom_categories


def test_classify_change_uses_builtin_map_when_configured_categories_are_empty(tmp_path: Path):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        "audit_input:\n  file_categories: []\n",
        encoding="utf-8",
    )
    refresh_audit_rules(path=rules_file)

    try:
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
    finally:
        refresh_audit_rules(path=tmp_path / "missing.yaml")


def test_missing_or_invalid_rules_file_keeps_safe_defaults(tmp_path: Path):
    assert load_audit_rules(path=tmp_path / "missing.yaml") == DEFAULT_RULES
    broken = tmp_path / "broken.yaml"
    broken.write_text("display: [not-a-mapping]", encoding="utf-8")
    assert load_audit_rules(path=broken) == DEFAULT_RULES


def test_refresh_injects_a_rules_file_for_tests(tmp_path: Path):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text("display:\n  calendar_labels:\n    X: 标签\n", encoding="utf-8")
    assert refresh_audit_rules(path=rules_file)["display"]["calendar_labels"] == {"X": "标签"}
    refresh_audit_rules(path=tmp_path / "missing.yaml")
