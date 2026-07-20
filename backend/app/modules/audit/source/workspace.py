from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

from app.settings import RuntimeSecuritySettings, get_runtime_security_settings, resolve_local_roots


IGNORED_WORKSPACE_DIRS = {
    ".git",
    ".svn",
    "__pycache__",
    ".idea",
    ".vscode",
}


class WorkspaceInfo(TypedDict):
    source_type: str
    source_label: str
    workspace_root: str
    exported_paths: list[str]
    branch_changed_files: list[str]
    trunk_changed_files: list[str]
    trunk_conflict_files: list[str]
    changes: list[str]
    files: list[str]
    project_type: str
    error: str


def _build_workspace_info(
    *,
    source_type: str,
    source_label: str,
    workspace_root: str,
    exported_paths: list[str],
    branch_changed_files: list[str],
    trunk_changed_files: list[str],
    trunk_conflict_files: list[str],
    project_type: str,
    error: str = "",
) -> WorkspaceInfo:
    return {
        "source_type": source_type,
        "source_label": source_label,
        "workspace_root": workspace_root,
        "exported_paths": exported_paths,
        "branch_changed_files": branch_changed_files,
        "trunk_changed_files": trunk_changed_files,
        "trunk_conflict_files": trunk_conflict_files,
        "changes": branch_changed_files,
        "files": exported_paths,
        "project_type": project_type,
        "error": error,
    }


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_local_workspace(local_dir: str, security_settings: RuntimeSecuritySettings | None = None) -> Path:
    raw_value = (local_dir or "").strip()
    if not raw_value:
        raise ValueError("Local workspace path is required")
    if raw_value.startswith("\\\\") or raw_value.startswith("//"):
        raise ValueError("UNC local workspace paths are not allowed")

    settings = security_settings or get_runtime_security_settings()
    if not settings.local_source_enabled:
        raise PermissionError("Local workspace audit source is disabled.")
    allowed_roots = resolve_local_roots(settings)
    if not allowed_roots:
        raise ValueError("Local workspace roots must be configured when local source is enabled")

    workspace_root = Path(raw_value).expanduser()
    if not workspace_root.exists():
        raise FileNotFoundError("Local workspace does not exist")
    if not workspace_root.is_dir():
        raise NotADirectoryError("Local workspace is not a directory")
    resolved_workspace = workspace_root.resolve()
    if not any(_is_within(resolved_workspace, root) for root in allowed_roots):
        raise PermissionError("Local workspace path is outside configured roots")
    return resolved_workspace


def load_local_workspace(
    local_dir: str,
    project_type: str = "hcyt",
    security_settings: RuntimeSecuritySettings | None = None,
) -> WorkspaceInfo:
    project = (project_type or "hcyt").strip().lower()
    workspace_root = validate_local_workspace(local_dir, security_settings)
    relative_file_paths: list[str] = []

    for current_root, dir_names, file_names in os.walk(workspace_root, topdown=True):
        safe_dirs = []
        for name in sorted(dir_names):
            candidate = Path(current_root) / name
            if name in IGNORED_WORKSPACE_DIRS or candidate.is_symlink() or not _is_within(candidate.resolve(), workspace_root):
                continue
            safe_dirs.append(name)
        dir_names[:] = safe_dirs
        for file_name in sorted(file_names):
            file_path = Path(current_root) / file_name
            resolved_file = file_path.resolve()
            if file_path.is_symlink() or not _is_within(resolved_file, workspace_root) or not resolved_file.is_file():
                continue
            relative_file_paths.append(resolved_file.relative_to(workspace_root).as_posix())

    relative_file_paths.sort()
    if not relative_file_paths:
        raise ValueError("Local workspace has no auditable files")

    exported_paths = [str((workspace_root / relative_path).resolve()) for relative_path in relative_file_paths]
    return _build_workspace_info(
        source_type="local",
        source_label=workspace_root.name or "local-workspace",
        workspace_root=str(workspace_root),
        exported_paths=exported_paths,
        branch_changed_files=relative_file_paths,
        trunk_changed_files=[],
        trunk_conflict_files=[],
        project_type=project,
    )


def load_svn_workspace(project: str, branch_url: str) -> WorkspaceInfo:
    from .svn import svn_main

    project_type = (project or "hcyt").strip().lower()
    svn_result = svn_main(project_type, branch_url)
    exported_paths = svn_result.get("exported_paths", [])
    resolved_exported_paths = [str(Path(path_str).resolve()) for path_str in exported_paths]
    workspace_root = ""
    if resolved_exported_paths:
        workspace_root = os.path.commonpath(resolved_exported_paths)

    return _build_workspace_info(
        source_type="svn",
        source_label=branch_url,
        workspace_root=workspace_root,
        exported_paths=resolved_exported_paths,
        branch_changed_files=svn_result.get("branch_changed_files", []),
        trunk_changed_files=svn_result.get("trunk_changed_files", []),
        trunk_conflict_files=svn_result.get("trunk_conflict_files", []),
        project_type=project_type,
    ) | {
        "create_revision": svn_result.get("create_revision", ""),
        "trunk_url": svn_result.get("trunk_url", ""),
        "branch_url": branch_url,
    }
