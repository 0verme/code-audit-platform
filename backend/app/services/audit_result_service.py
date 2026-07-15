import json

from app.db.runtime_store import list_audit_results, list_fine_report_items


def get_results(task_id: int | None) -> list[dict]:
    return [dict(row) for row in list_audit_results(task_id)]


def get_fine_report_items() -> list[dict]:
    items = []
    for row in list_fine_report_items():
        item = dict(row)
        item["issues"] = json.loads(item.pop("issues_json"))
        item["ref_tables"] = json.loads(item.pop("ref_tables_json"))
        items.append(item)
    return items
