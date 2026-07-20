from __future__ import annotations


def format_duration(elapsed_seconds: float) -> str:
    total = max(0, int(elapsed_seconds))
    if total < 60:
        return f"{total}秒"
    if total < 3600:
        minutes, seconds = divmod(total, 60)
        return f"{minutes}分{seconds:02d}秒"
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}时{minutes:02d}分{seconds:02d}秒"


def normalize_table(name) -> str:
    return "" if name is None else str(name).strip().upper()


def dedupe_tables(names):
    seen, result = set(), []
    for name in names or []:
        normalized = normalize_table(name)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
