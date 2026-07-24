"""Local OpenAI-compatible model client used by the optional AI review stage."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app.settings import get_local_llm_settings


PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
MAX_SOURCE_CHARS = 12_000


def _read_prompt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _prompt_for(path: Path) -> str:
    suffix = path.suffix.lower()
    name = "python_review.txt" if suffix == ".py" else "sql_review.txt" if suffix in {".sql", ".hql"} else "generic_review.txt"
    return _read_prompt(PROMPTS_DIR / name) or _read_prompt(PROMPTS_DIR / "generic_review.txt")


def _extract_json(content: str) -> dict[str, Any] | None:
    """Accept a JSON object, including the common markdown fenced form."""
    content = (content or "").strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0].strip()
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _normalise_result(value: dict[str, Any]) -> dict[str, Any] | None:
    findings = []
    raw_findings = value.get("findings", [])
    if not isinstance(raw_findings, list):
        raw_findings = []
    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity", "info")).lower()
        findings.append({
            "sev": severity if severity in {"info", "warn", "err"} else "info",
            "title": str(item.get("title") or "AI review finding")[:200],
            "body": str(item.get("suggestion") or item.get("evidence") or "")[:2_000],
            "lineStart": item.get("line_start"),
            "confidence": item.get("confidence"),
        })
    return {"summary": str(value.get("summary") or "No AI findings.")[:1_000], "findings": findings}


def call_sql_llm(source_path: str) -> dict[str, Any] | None:
    """Review one local source file through an OpenAI-compatible chat endpoint.

    Set LOCAL_LLM_BASE_URL and LOCAL_LLM_MODEL to enable it.  The API key is
    optional because many internal gateways authenticate by network policy.
    """
    settings = get_local_llm_settings()
    if not settings.enabled:
        return None

    path = Path(source_path)
    try:
        source = path.read_text(encoding="utf-8", errors="replace")[:MAX_SOURCE_CHARS]
    except OSError:
        return None
    if not source.strip():
        return None

    system_prompt = _prompt_for(path)
    payload = {
        "model": settings.model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"File: {path.name}\n\n<source>\n{source}\n</source>"},
        ],
    }
    headers = {"Content-Type": "application/json"}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"
    request = urllib.request.Request(
        f"{settings.base_url}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.HTTPError, urllib.error.URLError):
        return None
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    parsed = _extract_json(str(content))
    return _normalise_result(parsed) if parsed else None
