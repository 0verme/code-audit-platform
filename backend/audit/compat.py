from __future__ import annotations


def legacy_audit_result_row(
    *,
    file: str = "",
    line: int = 0,
    rule: str = "",
    level: str = "info",
    msg: str = "",
) -> dict:
    return {
        "file": file or "",
        "line": int(line or 0),
        "rule": rule or "",
        "level": level or "info",
        "msg": msg or "",
    }


def normalize_legacy_audit_result_groups(grouped_rows: dict[str, list[dict]] | None) -> dict[str, list[dict]]:
    normalized: dict[str, list[dict]] = {}
    for category, rows in (grouped_rows or {}).items():
        normalized[str(category or "")] = [
            legacy_audit_result_row(
                file=row.get("file", ""),
                line=row.get("line", 0),
                rule=row.get("rule", ""),
                level=row.get("level", "info"),
                msg=row.get("msg", ""),
            )
            for row in (rows or [])
        ]
    return normalized


def build_legacy_partial_report(partial_report: dict | None, final_report: dict | None) -> dict:
    payload = dict(partial_report or {})
    if final_report is not None:
        payload.setdefault("finalReport", final_report)
    return payload


def build_audit_run_partial_result_payload(task_id: int, status_payload: dict, final_report: dict | None) -> dict:
    return {
        "runId": task_id,
        "workflow": status_payload.get("workflow", ""),
        "status": status_payload.get("status", ""),
        "taskStatus": status_payload.get("taskStatus"),
        "progress": status_payload.get("progress", {}),
        "tasks": status_payload.get("tasks", {}),
        "partialReport": build_legacy_partial_report(status_payload.get("partialReport"), final_report),
        "finalReportReady": final_report is not None,
        "report": final_report,
        "logs": status_payload.get("logs", []),
    }


def build_legacy_nups_audit_result_rows(sql_checks: list[dict], rule_label_fn) -> dict[str, list[dict]]:
    return {
        "nups": [
            legacy_audit_result_row(
                file=check.get("script", ""),
                line=0,
                rule=rule_label_fn(message.get("msg")),
                level=message.get("level", "info"),
                msg=message.get("msg", ""),
            )
            for check in (sql_checks or [])
            for message in (check.get("messages") or [])
        ]
    }


def build_legacy_fine_audit_result_rows(reports: list[dict]) -> dict[str, list[dict]]:
    return {
        "fine": [
            legacy_audit_result_row(
                file=report.get("file", ""),
                line=0,
                rule=issue.get("rule", ""),
                level=issue.get("level", "info"),
                msg=issue.get("msg", ""),
            )
            for report in (reports or [])
            for issue in (report.get("issues") or [])
        ]
    }
