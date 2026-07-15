from __future__ import annotations

from app.settings import RuntimeSecuritySettings, get_runtime_security_settings


SUPPORTED_AUDIT_SOURCE_TYPES = frozenset({"svn", "local"})
GIT_SOURCE_UNSUPPORTED_MESSAGE = "Git audit source is not supported in the current version."


class UnsupportedAuditSourceError(ValueError):
    """Raised when a recognized audit source has no loader in this version."""


class LocalSourceDisabledError(ValueError):
    """Raised before a local workspace loader is allowed to run."""


def validate_supported_source_type(source_type: str) -> str:
    normalized = str(source_type or "").strip().lower()
    if normalized in SUPPORTED_AUDIT_SOURCE_TYPES:
        return normalized
    if normalized == "git":
        raise UnsupportedAuditSourceError(GIT_SOURCE_UNSUPPORTED_MESSAGE)
    raise UnsupportedAuditSourceError(f"Audit source type '{normalized or 'unknown'}' is not supported.")


def resolve_workflow(source_ref: str, fallback: str = "hcyt") -> str:
    if "/hcyt/" in source_ref:
        return "hcyt"
    if (
        "/NUPS/" in source_ref
        or "/nups/" in source_ref
        or "\\NUPS\\" in source_ref
        or "\\nups\\" in source_ref
    ):
        return "nups"
    if "fine-report" in source_ref:
        return "fine-report"
    return fallback or "hcyt"


def validate_source_workflow(source_type: str, workflow: str) -> None:
    if source_type == "local" and workflow != "hcyt":
        raise ValueError("Local workspace source currently supports hcyt workflow only")


def resolve_workspace(
    source_ref: str,
    workflow: str,
    source_type: str,
    *,
    svn_loader,
    local_loader,
    security_settings: RuntimeSecuritySettings | None = None,
) -> dict:
    source_type = validate_supported_source_type(source_type)
    if source_type == "local":
        validate_source_workflow(source_type, workflow)
        settings = security_settings or get_runtime_security_settings()
        if not settings.local_source_enabled:
            raise LocalSourceDisabledError("Local workspace audit source is disabled.")
        return local_loader(source_ref, workflow)
    payload = svn_loader(source_ref)
    return normalize_source_payload(payload, source_type=source_type)


def build_source_label(source_ref: str, source_type: str) -> str:
    if source_type == "local":
        return "local workspace"
    return source_ref


def build_source_load_step(source_type: str) -> str:
    if source_type == "local":
        return "读取本地目录"
    return "拉取 SVN"


def normalize_source_payload(payload: dict, *, source_type: str) -> dict:
    source_type = validate_supported_source_type(source_type)
    if source_type == "local":
        return payload
    normalized = dict(payload)
    normalized["source_type"] = "svn"
    normalized["workspace_root"] = ""
    return normalized


def build_source_summary(payload: dict, *, source_ref: str, fallback_source_type: str) -> dict:
    return {
        "sourceType": payload.get("source_type", fallback_source_type),
        "sourceRef": source_ref,
        "workspaceRoot": payload.get("workspace_root", ""),
    }


def detect_workflow(branch_url: str, fallback: str = "hcyt") -> str:
    return resolve_workflow(branch_url, fallback)


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
