from __future__ import annotations

from pathlib import PurePosixPath

from app.modules.lineage.identifiers import normalize_registered_table_name


def _text(value) -> str:
    return str(value or "").strip()


def _path(value) -> str:
    return _text(value).replace("\\", "/")


def _unique(values, *, normalize=False) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        item = normalize_registered_table_name(value) if normalize else _text(value)
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _change_type(program_path: str, script_name: str, changes) -> str:
    candidates = []
    normalized_path = program_path.casefold()
    normalized_name = script_name.casefold()
    for change in changes or []:
        change_path = _path(change.get("path")).casefold()
        if change_path and (
            change_path == normalized_path
            or change_path.endswith(f"/{normalized_path}")
            or (normalized_name and change_path.endswith(f"/{normalized_name}"))
        ):
            candidates.append(_text(change.get("type")))
    return candidates[0] if len(set(candidates)) == 1 else "modified"


def build_lineage_overlay(py_scripts, *, revision="", changes=None) -> dict:
    programs = []
    for script in py_scripts or []:
        program_path = _path(script.get("path") or script.get("script"))
        script_name = _text(script.get("script")) or PurePosixPath(program_path).name
        job_name = _text(script.get("job"))
        lineage_key = _text(script.get("lineageKey"))
        if not lineage_key:
            lineage_key = f"job:{job_name.upper()}" if job_name else f"program:{program_path.casefold()}"
        sql_inputs = script.get("inputTables")
        if sql_inputs is None:
            sql_inputs = [row.get("sql") for row in script.get("result") or [] if row.get("sql")]
            sql_inputs += list(script.get("codeval") or []) + list(script.get("temp") or [])
        programs.append({
            "lineageKey": lineage_key,
            "programPath": program_path,
            "scriptName": script_name,
            "jobName": job_name,
            "resultTable": normalize_registered_table_name(script.get("table")),
            "inputTables": _unique(sql_inputs, normalize=True),
            "dependencyJobs": _unique(script.get("dependencyJobs") or []),
            "frequency": _text(script.get("freq")),
            "disabled": bool(script.get("jobDisabled")),
            "changeType": _text(script.get("changeType")) or _change_type(program_path, script_name, changes),
        })
    return {
        "schemaVersion": "1.0",
        "revision": _text(revision),
        "programs": programs,
    }
