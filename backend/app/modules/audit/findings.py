from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Literal


FindingLevel = Literal["err", "warn", "info"]
VALID_FINDING_LEVELS = frozenset({"err", "warn", "info"})


@dataclass(frozen=True, slots=True)
class Finding:
    rule_code: str
    rule: str
    level: FindingLevel
    msg: str
    file: str | None = None
    line: int | None = None
    category: str | None = None
    location: str | None = None
    evidence: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        for field_name in ("rule_code", "rule", "msg"):
            if not str(getattr(self, field_name) or "").strip():
                raise ValueError(f"finding {field_name} must not be empty")
        if self.level not in VALID_FINDING_LEVELS:
            raise ValueError(f"unsupported finding level: {self.level}")

    def with_context(
        self,
        *,
        file: str | None = None,
        line: int | None = None,
        category: str | None = None,
        location: str | None = None,
    ) -> Finding:
        return replace(
            self,
            file=self.file if self.file is not None else file,
            line=self.line if self.line is not None else line,
            category=self.category if self.category is not None else category,
            location=self.location if self.location is not None else location,
        )

    def to_dict(self, *, include_context: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ruleCode": self.rule_code,
            "rule": self.rule,
            "level": self.level,
            "msg": self.msg,
        }
        if include_context:
            for key, value in (
                ("file", self.file),
                ("line", self.line),
                ("category", self.category),
                ("location", self.location),
                ("evidence", self.evidence),
            ):
                if value is not None:
                    payload[key] = value
        return payload


@dataclass(slots=True)
class CheckResult:
    findings: list[Finding] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.findings)

    def add(
        self,
        rule_code: str,
        rule: str,
        level: FindingLevel,
        msg: str,
        **context: Any,
    ) -> Finding:
        finding = Finding(rule_code, rule, level, msg, **context)
        self.findings.append(finding)
        return finding


def finding_rows(
    findings: list[Finding],
    *,
    file: str | None = None,
    category: str | None = None,
    location: str | None = None,
) -> list[dict[str, Any]]:
    rows = []
    for item in findings:
        enriched = item.with_context(file=file, category=category, location=location)
        row = enriched.to_dict()
        row.setdefault("file", "")
        row.setdefault("line", None)
        rows.append(row)
    return rows


def finding_messages(findings: list[Finding]) -> list[dict[str, Any]]:
    return [item.to_dict(include_context=False) for item in findings]
