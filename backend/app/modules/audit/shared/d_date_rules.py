from __future__ import annotations

import re


_IDENTIFIER_CHARS = r"A-Z0-9_$"
_D_DATE_IDENTIFIER = rf"(?<![{_IDENTIFIER_CHARS}])D_DATE(?![{_IDENTIFIER_CHARS}])"
_QUALIFIED_D_DATE = (
    rf"(?:[A-Z_][A-Z0-9_$]*\s*\.\s*)?{_D_DATE_IDENTIFIER}"
)

_D_DATE_RULE_PATTERNS = {
    "d_date_to_date": re.compile(
        rf"{_D_DATE_IDENTIFIER}\s*=\s*TO_DATE\s*\(\s*'",
        re.IGNORECASE,
    ),
    "d_date_literal": re.compile(
        rf"{_D_DATE_IDENTIFIER}\s*=\s*DATE\s*'",
        re.IGNORECASE,
    ),
    "d_date_function": re.compile(
        rf"(?<![{_IDENTIFIER_CHARS}])DATE(?![{_IDENTIFIER_CHARS}])"
        rf"\s*\(\s*{_QUALIFIED_D_DATE}\s*\)",
        re.IGNORECASE,
    ),
    "to_date_d_date": re.compile(
        rf"(?<![{_IDENTIFIER_CHARS}])TO_DATE(?![{_IDENTIFIER_CHARS}])"
        rf"\s*\(\s*{_QUALIFIED_D_DATE}\s*,",
        re.IGNORECASE,
    ),
    "d_date_less_than": re.compile(
        rf"{_D_DATE_IDENTIFIER}\s*<",
        re.IGNORECASE,
    ),
    "d_date_greater_than": re.compile(
        rf"{_D_DATE_IDENTIFIER}\s*>",
        re.IGNORECASE,
    ),
}


def detect_d_date_issues(sql_text: str) -> set[str]:
    """Return date-rule keys that reference the complete ``d_date`` identifier."""
    text = str(sql_text or "")
    return {
        rule_key
        for rule_key, pattern in _D_DATE_RULE_PATTERNS.items()
        if pattern.search(text)
    }
