from __future__ import annotations

from app.settings import RuntimeSecuritySettings, get_runtime_security_settings
from app.config.audit_rules import get_audit_rules


SUPPORTED_AUDIT_SOURCE_TYPES = frozenset({"svn", "local"})
SUPPORTED_LOCAL_WORKFLOWS = frozenset({"hcyt", "nups", "fine-report"})
LOCAL_WORKFLOW_UNSUPPORTED_MESSAGE = (
    "Local workspace source currently supports hcyt, nups, and fine-report workflows only"
)
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
    normalized = str(source_ref or "").replace("\\", "/").lower()
    workflows = get_audit_rules()["workflows"]
    for definition in workflows["definitions"]:
        if not isinstance(definition, dict) or not isinstance(definition.get("id"), str):
            continue
        if any(str(keyword).lower() in normalized for keyword in definition.get("path_keywords", [])):
            return definition["id"]
    return fallback or workflows["default"]


def validate_source_workflow(source_type: str, workflow: str) -> None:
    if source_type == "local" and workflow not in SUPPORTED_LOCAL_WORKFLOWS:
        raise ValueError(LOCAL_WORKFLOW_UNSUPPORTED_MESSAGE)


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
    for rule in get_audit_rules()["audit_input"]["file_categories"]:
        if not isinstance(rule, dict) or not isinstance(rule.get("category"), str):
            continue
        contains = rule.get("contains")
        suffixes = rule.get("suffixes", [])
        if contains and contains not in lower:
            continue
        if suffixes and not lower.endswith(tuple(suffixes)):
            continue
        if contains or suffixes:
            return rule["category"]
    return "其他"
