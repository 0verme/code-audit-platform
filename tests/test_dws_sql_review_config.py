import sys
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config.audit_rules import load_audit_rules, refresh_audit_rules  # noqa: E402
from app.modules.audit.checks import nups_rule  # noqa: E402
from app.modules.audit.checks.dws_sql_review import run_configured_dws_sql_reviews  # noqa: E402
from app.modules.audit.checks.hcyt import sql_rule  # noqa: E402


def test_tracked_example_declares_default_sql_review_rules():
    rules = load_audit_rules(path=BACKEND_DIR / "configs" / "audit_rules.example.yaml")

    assert rules["dws"]["sql_review"]["legacy_markers"][1] == {
        "value": "LZY",
        "excludes": ["RLZY"],
    }
    assert rules["dws"]["sql_review"]["protected_code_tables"] == [
        "DWM.M_PUB_CODE_MAP_NEW",
        "DWM.M_PUB_CODE_INFO_NEW",
        "DWM.M_PUB_CODE_USE_NEW",
    ]


def test_default_rules_match_legacy_markers_and_code_tables(tmp_path: Path):
    refresh_audit_rules(path=tmp_path / "missing.yaml")

    messages = run_configured_dws_sql_reviews(
        "select wlq, lzy, bsc, ygw, tmpqs from dwm.m_pub_code_map_new",
        message_style="hcyt",
    )

    assert messages == [
        "建表脚本带WLQ,请确认是不是取数单的表名没改",
        "建表脚本带LZY,请确认是不是取数单的表名没改",
        "建表脚本带BSC,请确认是不是取数单的表名没改",
        "建表脚本带YGW,请确认是不是取数单的表名没改",
        "建表脚本带TMPQS,请确认是不是取数单的表名没改",
        "存在码值表M_PUB_CODE_MAP_NEW修改,请审核重点检查",
    ]


def test_marker_exclusion_and_case_insensitive_matching(tmp_path: Path):
    refresh_audit_rules(path=tmp_path / "missing.yaml")

    messages = run_configured_dws_sql_reviews(
        "select rlzy from DWM.M_PUB_CODE_INFO_NEW",
        message_style="hcyt",
    )

    assert messages == ["存在码值表M_PUB_CODE_INFO_NEW修改,请审核重点检查"]


def test_yaml_replaces_default_review_values(tmp_path: Path):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        """dws:
  sql_review:
    legacy_markers:
      - {value: custom_tag, excludes: [ignore_custom_tag]}
    protected_code_tables: [ODS.CUSTOM_CODE]
""",
        encoding="utf-8",
    )

    try:
        refresh_audit_rules(path=rules_file)
        default_messages = run_configured_dws_sql_reviews(
            "WLQ DWM.M_PUB_CODE_MAP_NEW",
            message_style="hcyt",
        )
        custom_messages = run_configured_dws_sql_reviews(
            "custom_tag ods.custom_code",
            message_style="hcyt",
        )
        excluded_messages = run_configured_dws_sql_reviews(
            "ignore_custom_tag",
            message_style="hcyt",
        )
    finally:
        refresh_audit_rules(path=tmp_path / "missing.yaml")

    assert default_messages == []
    assert custom_messages == [
        "建表脚本带CUSTOM_TAG,请确认是不是取数单的表名没改",
        "存在码值表CUSTOM_CODE修改,请审核重点检查",
    ]
    assert excluded_messages == []


def test_hcyt_rule_dws_uses_configured_reviews(tmp_path: Path):
    refresh_audit_rules(path=tmp_path / "missing.yaml")
    with (
        patch.object(sql_rule, "read_data_from_file", return_value="wlq"),
        patch.object(sql_rule, "all_view_names", return_value=[]),
        patch.object(sql_rule, "all_function_names", return_value=[]),
        patch.object(sql_rule, "run_dws_ddl_rules", return_value=[]),
    ):
        result_text, warning_text, count = sql_rule.rule_dws("dws.sql")

    assert result_text == "建表脚本带WLQ,请确认是不是取数单的表名没改\n"
    assert warning_text == "存在dws.sql\n"
    assert count == 1


def test_nups_rule_dws_uses_configured_reviews(tmp_path: Path):
    refresh_audit_rules(path=tmp_path / "missing.yaml")
    with (
        patch.object(nups_rule, "read_data_from_file", return_value="dwm.m_pub_code_use_new"),
        patch.object(nups_rule, "all_view_names", return_value=[]),
        patch.object(nups_rule, "all_function_names", return_value=[]),
        patch.object(nups_rule, "run_dws_ddl_rules", return_value=[]),
    ):
        result_text, count = nups_rule.rule_dws("nups.sql")

    assert result_text == (
        "存在对 dwm 模型层的操作，请审核重点检查\n"
        "存在码值表 M_PUB_CODE_USE_NEW 修改，请审核重点检查\n"
    )
    assert count == 2
