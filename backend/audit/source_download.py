from __future__ import annotations

from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlsplit


def normalize_relative_path(value: str) -> str:
    """Normalize a report path without accepting an absolute or escaping path."""
    raw = str(value or "").replace("\\", "/").strip()
    if not raw or raw.startswith("/") or raw.startswith("//") or ":" in raw.split("/", 1)[0]:
        raise ValueError("invalid source file path")
    path = PurePosixPath(raw)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("invalid source file path")
    return path.as_posix()


def build_source_download_url(task_id: int, relative_path: str) -> str:
    normalized = normalize_relative_path(relative_path)
    return f"/api/audit-tasks/{int(task_id)}/source-file?path={quote(normalized, safe='/')}"


def source_relative_paths(exported_paths, workspace_root: str) -> dict[str, str]:
    root = Path(workspace_root).resolve()
    paths = {}
    for value in exported_paths or []:
        resolved = Path(value).resolve()
        try:
            relative = resolved.relative_to(root).as_posix()
        except ValueError:
            continue
        paths[str(resolved)] = normalize_relative_path(relative)
    return paths


def source_relative_paths_from_changes(exported_paths, changed_paths) -> dict[str, str]:
    """Match exported SVN files to their repository-relative changed paths."""
    candidates = [normalize_relative_path(value) for value in changed_paths or []]
    paths = {}
    for value in exported_paths or []:
        resolved = Path(value).resolve()
        parts = resolved.parts
        for relative in candidates:
            relative_parts = PurePosixPath(relative).parts
            if len(parts) >= len(relative_parts) and tuple(parts[-len(relative_parts):]) == relative_parts:
                paths[str(resolved)] = relative
                break
    return paths


def svn_export_root(source_ref: str, export_base: Path) -> Path:
    branch_name = unquote(urlsplit(str(source_ref or "")).path.rstrip("/").rsplit("/", 1)[-1])
    if not branch_name or branch_name in {".", ".."} or "/" in branch_name or "\\" in branch_name:
        raise ValueError("invalid SVN branch name")
    return (Path(export_base).resolve() / branch_name).resolve()


def allowed_report_paths(report: dict) -> set[str]:
    paths = set()
    for change in report.get("changes", []) or []:
        if not isinstance(change, dict):
            continue
        try:
            paths.add(normalize_relative_path(change.get("path", "")))
        except ValueError:
            continue
    return paths


def resolve_source_download_path(*, task: dict, report: dict, relative_path: str, export_base: Path) -> Path:
    normalized = normalize_relative_path(relative_path)
    if normalized not in allowed_report_paths(report):
        raise FileNotFoundError("source file is not part of this audit task")
    source_type = str(task.get("source_type") or "").lower()
    if source_type == "local":
        root = Path(task.get("source_ref") or task.get("repo") or "").resolve()
    elif source_type == "svn":
        root = svn_export_root(task.get("source_ref") or task.get("repo") or "", export_base)
    else:
        raise FileNotFoundError("unsupported audit source")
    candidate = (root / Path(*PurePosixPath(normalized).parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("invalid source file path") from exc
    if not candidate.is_file():
        raise FileNotFoundError("source file does not exist")
    return candidate
