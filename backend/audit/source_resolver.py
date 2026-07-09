from __future__ import annotations


def detect_workflow(branch_url: str, fallback: str = "hcyt") -> str:
    if "/hcyt/" in branch_url:
        return "hcyt"
    if "/NUPS/" in branch_url or "/nups/" in branch_url:
        return "nups"
    if "/fine-report/" in branch_url:
        return "fine-report"
    return fallback or "hcyt"


def classify_change(path: str) -> str:
    lower = path.lower()
    if "dws.sql" in lower:
        return "DWS SQL"
    if "hive.sql" in lower:
        return "Hive SQL"
    if lower.endswith(".sql"):
        return "SQL"
    if lower.endswith(".py"):
        return "Python"
    if lower.endswith(".sh") or "/sbin/" in lower:
        return "后置脚本"
    if lower.endswith((".xls", ".xlsx")):
        return "调度表"
    if lower.endswith(".json"):
        return "配置文件"
    if lower.endswith((".cpt", ".frm")):
        return "报表模板"
    if lower.endswith(".txt"):
        return "目录/权限"
    return "其他"
