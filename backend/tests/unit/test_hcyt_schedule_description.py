from app.config.audit_rules import get_audit_rules
from app.modules.audit.workflows.hcyt.checks.schedule_rule import (
    _job_description_error_message,
)


def test_description_error_omits_reference_when_url_is_empty():
    rules = get_audit_rules()["hcyt"]["schedule"]["description_validation"]

    message = _job_description_error_message("JOB_A", rules)

    assert "参考：" not in message
    assert "https://example.com" not in message


def test_description_error_includes_configured_reference_url():
    rules = {
        **get_audit_rules()["hcyt"]["schedule"]["description_validation"],
        "reference_url": " https://docs.example.test/job-description ",
    }

    message = _job_description_error_message("JOB_A", rules)

    assert message == (
        "JOB_A 第四列作业描述必须要明确加工作用 "
        "参考：https://docs.example.test/job-description"
    )
