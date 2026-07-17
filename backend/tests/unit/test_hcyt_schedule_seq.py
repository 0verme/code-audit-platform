from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from app.modules.audit.checks.hcyt.schedule_rule import rule_excle_seq
from app.modules.audit.hcyt_schedule_runner import run_hcyt_schedule


def _seq_frame(seq_name):
    return pd.DataFrame(
        [["PLAN_TEST", seq_name, "测试作业流"]],
        columns=["计划名", "作业流名", "作业流描述"],
    )


def test_real_sequence_from_database_row_produces_warning():
    with patch(
        "app.modules.audit.checks.hcyt.schedule_rule.all_real_seq",
        return_value=[("SEQ_REAL_X",)],
    ):
        result = rule_excle_seq(_seq_frame("SEQ_REAL_X"))

    assert "作业流名：SEQ_REAL_X" in result.findings[0].msg
    assert "作业流是循环作业" in result.findings[0].msg
    assert result.findings[0].rule_code == "hcyt.schedule.seq.realtime_override"
    assert result.count == 1


def test_non_real_sequence_does_not_produce_warning():
    with patch(
        "app.modules.audit.checks.hcyt.schedule_rule.all_real_seq",
        return_value=[("SEQ_REAL_X",)],
    ):
        assert rule_excle_seq(_seq_frame("SEQ_BATCH_X")).count == 0


def test_empty_sequence_name_does_not_raise_or_produce_warning():
    with patch(
        "app.modules.audit.checks.hcyt.schedule_rule.all_real_seq",
        return_value=[("SEQ_REAL_X",)],
    ):
        assert rule_excle_seq(_seq_frame(None)).count == 0


def test_real_sequence_warning_is_added_to_schedule_report():
    frame = _seq_frame("SEQ_REAL_X")
    modules = SimpleNamespace(
        re_service=SimpleNamespace(load_xls_to_df=lambda _path: frame),
        hcyt=SimpleNamespace(rule_excle_seq=rule_excle_seq),
    )

    with patch(
        "app.modules.audit.checks.hcyt.schedule_rule.all_real_seq",
        return_value=[("SEQ_REAL_X",)],
    ):
        report = run_hcyt_schedule(
            None,
            "SEQ_test.xls",
            None,
            None,
            safe=lambda _label, fn, _default: fn(),
            modules=modules,
            build_job_table=lambda *_args, **_kwargs: ({}, []),
        )

    expected = {
        "table": "SEQ",
        "item": "SEQ_test.xls",
        "ruleCode": "hcyt.schedule.seq.realtime_override",
        "rule": "循环作业流覆盖",
        "level": "err",
        "msg": "作业流名：SEQ_REAL_X  作业流是循环作业,会覆盖生产的循环调度,需要删除不用上线",
    }
    assert report["rows"] == [expected]
    assert report["tables"]["seq"]["messages"] == [
        {key: value for key, value in expected.items() if key not in {"table", "item"}}
    ]
