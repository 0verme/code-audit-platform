"""Detect high-risk DWS and Hive SQL statements without executing SQL."""
from __future__ import annotations

from dataclasses import dataclass
import re

from ....shared.findings import Finding


_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*")
_COMMANDS = {
    "ALTER", "CREATE", "DELETE", "DROP", "GRANT", "INSERT",
    "LOAD", "REVOKE", "SELECT", "TRUNCATE", "UPDATE",
}
_DROP_OBJECT_TYPES = {
    "DATABASE", "FUNCTION", "INDEX", "MATERIALIZED VIEW",
    "SCHEMA", "TABLE", "VIEW",
}
_IDENTITY_TYPES = {"ROLE", "USER"}


@dataclass(frozen=True, slots=True)
class _Token:
    value: str
    raw: str
    line: int
    depth: int
    kind: str = "word"


def _tokenize(sql_text: str) -> list[_Token]:
    tokens: list[_Token] = []
    text = str(sql_text or "")
    line = 1
    depth = 0
    index = 0

    while index < len(text):
        char = text[index]
        if char.isspace():
            if char == "\n":
                line += 1
            index += 1
            continue
        if text.startswith("--", index):
            index += 2
            while index < len(text) and text[index] != "\n":
                index += 1
            continue
        if text.startswith("/*", index):
            index += 2
            while index < len(text) and not text.startswith("*/", index):
                if text[index] == "\n":
                    line += 1
                index += 1
            index = min(index + 2, len(text))
            continue
        if char == "'":
            index += 1
            while index < len(text):
                if text[index] == "\n":
                    line += 1
                if text[index] == "'":
                    if index + 1 < len(text) and text[index + 1] == "'":
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            continue
        if char in {'"', "`"}:
            quote = char
            token_line = line
            index += 1
            value_start = index
            parts = []
            while index < len(text):
                if text[index] == "\n":
                    line += 1
                if text[index] == quote:
                    if index + 1 < len(text) and text[index + 1] == quote:
                        parts.extend([text[value_start:index], quote])
                        index += 2
                        value_start = index
                        continue
                    parts.append(text[value_start:index])
                    index += 1
                    break
                index += 1
            raw_value = "".join(parts)
            tokens.append(_Token(raw_value.upper(), f"{quote}{raw_value}{quote}", token_line, depth, "identifier"))
            continue
        if char == "(":
            tokens.append(_Token(char, char, line, depth, "symbol"))
            depth += 1
            index += 1
            continue
        if char == ")":
            depth = max(depth - 1, 0)
            tokens.append(_Token(char, char, line, depth, "symbol"))
            index += 1
            continue
        if char in ";.,":
            tokens.append(_Token(char, char, line, depth, "symbol"))
            index += 1
            continue
        word_match = _WORD_RE.match(text, index)
        if word_match:
            raw = word_match.group(0)
            tokens.append(_Token(raw.upper(), raw, line, depth))
            index = word_match.end()
            continue
        tokens.append(_Token(char.upper(), char, line, depth, "symbol"))
        index += 1
    return tokens


def _split_statements(tokens: list[_Token]) -> list[list[_Token]]:
    statements: list[list[_Token]] = []
    current: list[_Token] = []
    for token in tokens:
        if token.value == ";" and token.depth == 0:
            if current:
                statements.append(current)
            current = []
        else:
            current.append(token)
    if current:
        statements.append(current)
    return statements


def _top_level_tokens(statement: list[_Token]) -> list[_Token]:
    return [token for token in statement if token.depth == 0 and token.value not in {"(", ","}]


def _command_index(tokens: list[_Token]) -> int | None:
    if not tokens:
        return None
    if tokens[0].kind == "word" and tokens[0].value != "WITH":
        return 0
    if tokens[0].value != "WITH":
        return None
    # CTE bodies are nested; the first command after one closes is executed.
    saw_cte_body = False
    for index, token in enumerate(tokens[1:], start=1):
        if token.value == ")":
            saw_cte_body = True
        elif saw_cte_body and token.kind == "word" and token.value in _COMMANDS:
            return index
    return None


def _sequence_at(tokens: list[_Token], index: int, *values: str) -> bool:
    return [token.value for token in tokens[index:index + len(values)]] == list(values)


def _skip_words(tokens: list[_Token], index: int, skipped: set[str]) -> int:
    while index < len(tokens) and tokens[index].value in skipped:
        index += 1
    return index


def _identifier_from(tokens: list[_Token], index: int) -> str:
    index = _skip_words(tokens, index, {"IF", "EXISTS", "ONLY", "TABLE"})
    if index >= len(tokens) or tokens[index].kind not in {"word", "identifier"}:
        return ""
    parts = [tokens[index].raw]
    index += 1
    while (
        index + 1 < len(tokens)
        and tokens[index].value == "."
        and tokens[index + 1].kind in {"word", "identifier"}
    ):
        parts.extend([".", tokens[index + 1].raw])
        index += 2
    return "".join(parts)


def _token_after(tokens: list[_Token], marker: str, *, skip: set[str] | None = None) -> str:
    for index, token in enumerate(tokens):
        if token.value == marker:
            return _identifier_from(tokens, _skip_words(tokens, index + 1, skip or set()))
    return ""


def _finding(
    *,
    namespace: str,
    suffix: str,
    rule: str,
    level: str,
    operation: str,
    line: int,
    object_name: str = "",
    principal: str = "",
) -> Finding:
    details = []
    if object_name:
        details.append(f"对象 {object_name}")
    if principal:
        details.append(f"主体 {principal}")
    detail_text = f"（{'，'.join(details)}）" if details else ""
    evidence = {"operation": operation, "line": line}
    if object_name:
        evidence["object"] = object_name
    if principal:
        evidence["principal"] = principal
    return Finding(
        f"{namespace}.{suffix}",
        rule,
        level,
        f"第 {line} 行检测到 {operation} 操作{detail_text}，请重点审核",
        location=f"第 {line} 行",
        evidence=evidence,
    )


def _scan_statement(statement: list[_Token], namespace: str) -> Finding | None:
    tokens = _top_level_tokens(statement)
    command_index = _command_index(tokens)
    if command_index is None:
        return None
    command = tokens[command_index].value
    tail = tokens[command_index:]
    line = tokens[command_index].line

    if command in {"GRANT", "REVOKE"}:
        principal_marker = "TO" if command == "GRANT" else "FROM"
        return _finding(
            namespace=namespace,
            suffix="permission_change",
            rule="权限变更",
            level="err",
            operation=command,
            line=line,
            object_name=_token_after(tail, "ON", skip={"DATABASE", "FUNCTION", "SCHEMA", "TABLE"}),
            principal=_token_after(tail, principal_marker, skip={"ROLE", "USER"}),
        )

    if command in {"CREATE", "ALTER", "DROP"} and len(tail) > 1 and tail[1].value in _IDENTITY_TYPES:
        identity_type = tail[1].value
        return _finding(
            namespace=namespace,
            suffix="identity_change",
            rule="用户或角色变更",
            level="err",
            operation=f"{command} {identity_type}",
            line=line,
            object_name=_identifier_from(tail, 2),
        )

    if command == "DROP" and len(tail) > 1:
        object_type = tail[1].value
        object_index = 2
        if _sequence_at(tail, 1, "MATERIALIZED", "VIEW"):
            object_type = "MATERIALIZED VIEW"
            object_index = 3
        if object_type in _DROP_OBJECT_TYPES:
            return _finding(
                namespace=namespace,
                suffix="destructive_ddl",
                rule="破坏性 DDL",
                level="err",
                operation=f"DROP {object_type}",
                line=line,
                object_name=_identifier_from(tail, object_index),
            )

    if command == "TRUNCATE":
        object_index = 2 if len(tail) > 1 and tail[1].value == "TABLE" else 1
        return _finding(
            namespace=namespace,
            suffix="destructive_ddl",
            rule="破坏性 DDL",
            level="err",
            operation="TRUNCATE TABLE",
            line=line,
            object_name=_identifier_from(tail, object_index),
        )

    if command == "ALTER" and len(tail) > 1 and tail[1].value == "TABLE":
        for index, token in enumerate(tail[2:], start=2):
            if token.value != "DROP":
                continue
            destructive_type = next(
                (item.value for item in tail[index + 1:index + 5] if item.value in {"COLUMN", "PARTITION"}),
                "",
            )
            if destructive_type:
                return _finding(
                    namespace=namespace,
                    suffix="destructive_ddl",
                    rule="破坏性 DDL",
                    level="err",
                    operation=f"ALTER TABLE DROP {destructive_type}",
                    line=line,
                    object_name=_identifier_from(tail, 2),
                )

    if command in {"UPDATE", "DELETE"}:
        if not any(token.value == "WHERE" for token in tail[1:]):
            object_index = 2 if command == "DELETE" and len(tail) > 1 and tail[1].value == "FROM" else 1
            return _finding(
                namespace=namespace,
                suffix="unbounded_dml",
                rule="无条件数据修改",
                level="err",
                operation=command,
                line=line,
                object_name=_identifier_from(tail, object_index),
            )
        return None

    if command == "INSERT" and len(tail) > 1 and tail[1].value == "OVERWRITE":
        return _finding(
            namespace=namespace,
            suffix="overwrite_write",
            rule="覆盖写入",
            level="warn",
            operation="INSERT OVERWRITE",
            line=line,
            object_name=_identifier_from(tail, 2),
        )

    if command == "LOAD" and any(token.value == "OVERWRITE" for token in tail[1:]):
        return _finding(
            namespace=namespace,
            suffix="overwrite_write",
            rule="覆盖写入",
            level="warn",
            operation="LOAD DATA OVERWRITE",
            line=line,
            object_name=_token_after(tail, "INTO"),
        )

    if command == "ALTER":
        object_type = tail[1].value if len(tail) > 1 else ""
        return _finding(
            namespace=namespace,
            suffix="alter_statement",
            rule="ALTER 命令",
            level="warn",
            operation=f"ALTER {object_type}".strip(),
            line=line,
            object_name=_identifier_from(tail, 2 if object_type else 1),
        )
    return None


def scan_sensitive_sql(sql_text: str, *, namespace: str) -> list[Finding]:
    """Return one highest-severity finding for each sensitive SQL statement."""
    findings = []
    for statement in _split_statements(_tokenize(sql_text)):
        finding = _scan_statement(statement, namespace)
        if finding is not None:
            findings.append(finding)
    return findings
