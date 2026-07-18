"""Validation helpers for HCYT schedule job descriptions."""
from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
import re
import unicodedata
from typing import Any


_CHINESE_CHARACTER_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_DEFAULT_MIN_MEANINGFUL_CHINESE_CHARACTERS = 2


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    return unicodedata.normalize("NFKC", str(value)).strip()


def _compact_text(value: object) -> str:
    return "".join(character for character in _normalize_text(value).casefold() if character.isalnum())


@lru_cache(maxsize=32)
def _compile_noise_pattern(noise_phrases: tuple[str, ...]) -> re.Pattern[str] | None:
    normalized_phrases = set(filter(None, map(_compact_text, noise_phrases)))
    if not normalized_phrases:
        return None
    alternatives = "|".join(
        re.escape(phrase)
        for phrase in sorted(normalized_phrases, key=len, reverse=True)
    )
    return re.compile(alternatives, re.IGNORECASE)


@lru_cache(maxsize=32)
def _normalized_invalid_values(invalid_values: tuple[str, ...]) -> frozenset[str]:
    return frozenset(_compact_text(value) for value in invalid_values)


def _rule_values(rules: Mapping[str, Any], key: str) -> tuple[str, ...]:
    values = rules.get(key, ())
    if not isinstance(values, (list, tuple)):
        return ()
    return tuple(str(value) for value in values)


def has_meaningful_job_description(
    description: object,
    job_name: object,
    rules: Mapping[str, Any],
) -> bool:
    """Return whether a description contains configurable Chinese business meaning."""
    normalized_description = _normalize_text(description)
    if not normalized_description:
        return False

    compact_description = _compact_text(normalized_description)
    invalid_values = _rule_values(rules, "invalid_values")
    if compact_description in _normalized_invalid_values(invalid_values):
        return False

    normalized_job_name = _compact_text(job_name)
    candidate = compact_description
    if normalized_job_name:
        candidate = re.sub(
            re.escape(normalized_job_name),
            "",
            candidate,
            flags=re.IGNORECASE,
        )

    noise_pattern = _compile_noise_pattern(_rule_values(rules, "noise_phrases"))
    if noise_pattern is not None:
        candidate = noise_pattern.sub("", candidate)

    meaningful_chinese = "".join(_CHINESE_CHARACTER_RE.findall(candidate))
    try:
        minimum_characters = int(
            rules.get(
                "min_meaningful_chinese_chars",
                _DEFAULT_MIN_MEANINGFUL_CHINESE_CHARACTERS,
            )
        )
    except (TypeError, ValueError):
        minimum_characters = _DEFAULT_MIN_MEANINGFUL_CHINESE_CHARACTERS
    minimum_characters = max(1, minimum_characters)

    if len(meaningful_chinese) < minimum_characters:
        return False

    job_name_chinese = "".join(_CHINESE_CHARACTER_RE.findall(normalized_job_name))
    if job_name_chinese and meaningful_chinese in job_name_chinese:
        return False
    return True
