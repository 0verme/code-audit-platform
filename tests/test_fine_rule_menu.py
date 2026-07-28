import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.workflows.fine_report.checks import rule_menu  # noqa: E402


def test_rule_menu_ignores_blank_lines_and_trailing_newline(tmp_path):
    menu_file = tmp_path / "menu.txt"
    menu_file.write_text(
        "数据仓库/报表管理/[FR001]合规报表.cpt,合规报表,分页预览\n\n",
        encoding="utf-8",
    )

    result = rule_menu(str(menu_file))

    assert result.findings == []
    assert result.artifacts["menu_entries"] == ["合规报表"]
