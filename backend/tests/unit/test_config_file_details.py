from app.modules.audit.shared.report_helpers import build_config_files


def test_build_config_files_preserves_valid_json_details(tmp_path):
    config_file = tmp_path / "schema.json"
    config_file.write_text('{"table": "DWM.CUSTOMER", "enabled": true}', encoding="utf-8")

    details = build_config_files([config_file])

    assert details == [{
        "name": "schema.json",
        "columns": ["字段", "值"],
        "rows": [["table", "DWM.CUSTOMER"], ["enabled", "True"]],
    }]


def test_build_config_files_keeps_parse_error_as_expandable_detail(tmp_path):
    config_file = tmp_path / "broken.json"
    config_file.write_text("{invalid", encoding="utf-8")

    details = build_config_files([config_file])

    assert details[0]["name"] == "broken.json"
    assert details[0]["columns"] == []
    assert details[0]["rows"] == []
    assert details[0]["error"].startswith("无法按 JSON 解析:")
