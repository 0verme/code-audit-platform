from pathlib import Path

from app.config.audit_rules import DEFAULT_RULES, load_audit_rules, refresh_audit_rules


def test_valid_rules_file_overrides_declared_values(tmp_path: Path):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        "display:\n  highlight_result_source_systems: [CRM]\nhcyt:\n  schedule:\n    allowed_domains: [DOMAIN_A]\n",
        encoding="utf-8",
    )
    rules = load_audit_rules(path=rules_file)
    assert rules["display"]["highlight_result_source_systems"] == ["CRM"]
    assert rules["hcyt"]["schedule"]["allowed_domains"] == ["DOMAIN_A"]


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
