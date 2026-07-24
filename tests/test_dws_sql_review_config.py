import copy
import sys
from pathlib import Path
from unittest.mock import patch

import yaml


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config.audit_rules import load_audit_rules, refresh_audit_rules  # noqa: E402
from app.modules.audit.shared.dws_sql_review import run_configured_dws_sql_reviews  # noqa: E402
from app.modules.audit.workflows.hcyt.checks import sql_rule  # noqa: E402
from app.modules.audit.workflows.nups import checks as nups_rule  # noqa: E402


RULES_PATH = BACKEND_DIR / "configs" / "audit_rules.yaml"


def test_tracked_rules_declare_sql_review_rules():
    rules = load_audit_rules(path=RULES_PATH)

    assert rules["dws"]["sql_review"]["legacy_markers"][1] == {
        "value": "LZY",
        "excludes": ["RLZY"],
    }
    assert rules["dws"]["sql_review"]["protected_code_tables"] == [
        "DWM.M_PUB_CODE_MAP_NEW",
        "DWM.M_PUB_CODE_INFO_NEW",
        "DWM.M_PUB_CODE_USE_NEW",
    ]


def test_configured_rules_match_legacy_markers_and_code_tables():
    refresh_audit_rules(path=RULES_PATH)

    findings = run_configured_dws_sql_reviews(
        "select wlq, lzy, bsc, ygw, tmpqs from dwm.m_pub_code_map_new",
        message_style="hcyt",
    )

    assert [item.msg for item in findings] == [
        "建表脚本带WLQ,请确认是不是取数单的表名没改",
        "建表脚本带LZY,请确认是不是取数单的表名没改",
        "建表脚本带BSC,请确认是不是取数单的表名没改",
        "建表脚本带YGW,请确认是不是取数单的表名没改",
        "建表脚本带TMPQS,请确认是不是取数单的表名没改",
        "存在码值表M_PUB_CODE_MAP_NEW修改,请审核重点检查",
    ]


def test_marker_exclusion_and_case_insensitive_matching():
    refresh_audit_rules(path=RULES_PATH)

    findings = run_configured_dws_sql_reviews(
        "select rlzy from DWM.M_PUB_CODE_INFO_NEW",
        message_style="hcyt",
    )

    assert [item.msg for item in findings] == ["存在码值表M_PUB_CODE_INFO_NEW修改,请审核重点检查"]


def test_yaml_replaces_default_review_values(tmp_path: Path):
    rules = copy.deepcopy(load_audit_rules(path=RULES_PATH))
    rules["dws"]["sql_review"] = {
        "legacy_markers": [
            {"value": "custom_tag", "excludes": ["ignore_custom_tag"]},
        ],
        "protected_code_tables": ["ODS.CUSTOM_CODE"],
    }
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        yaml.safe_dump(rules, allow_unicode=True, sort_keys=False),
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
        refresh_audit_rules(path=RULES_PATH)

    assert default_messages == []
    assert [item.msg for item in custom_messages] == [
        "建表脚本带CUSTOM_TAG,请确认是不是取数单的表名没改",
        "存在码值表CUSTOM_CODE修改,请审核重点检查",
    ]
    assert excluded_messages == []


def test_hcyt_rule_dws_uses_configured_reviews():
    refresh_audit_rules(path=RULES_PATH)
    with (
        patch.object(sql_rule, "read_data_from_file", return_value="wlq"),
        patch.object(sql_rule, "all_view_names", return_value=[]),
        patch.object(sql_rule, "all_function_names", return_value=[]),
        patch.object(sql_rule, "run_dws_ddl_rules", return_value=[]),
    ):
        result = sql_rule.rule_dws("dws.sql")

    assert [item.msg for item in result.findings] == [
        "存在dws.sql",
        "建表脚本带WLQ,请确认是不是取数单的表名没改",
    ]
    assert [item.level for item in result.findings] == ["info", "err"]


def test_nups_rule_dws_uses_configured_reviews():
    refresh_audit_rules(path=RULES_PATH)
    with (
        patch.object(nups_rule, "read_data_from_file", return_value="dwm.m_pub_code_use_new"),
        patch.object(nups_rule, "all_view_names", return_value=[]),
        patch.object(nups_rule, "all_function_names", return_value=[]),
        patch.object(nups_rule, "run_dws_ddl_rules", return_value=[]),
    ):
        result = nups_rule.rule_dws("nups.sql")

    assert [item.msg for item in result.findings] == [
        "存在对 dwm 模型层的操作，请审核重点检查",
        "存在码值表 M_PUB_CODE_USE_NEW 修改，请审核重点检查",
    ]
