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


def rule_label(line: str) -> str:
    for sep in ("：", ":", "，", ",", " "):
        idx = line.find(sep)
        if 0 < idx <= 30:
            return line[:idx]
    return line[:24] or "规则检查"


def text_to_rows(result_text, warn_text, file_name="", err_level="err", warn_level="warn"):
    """把规则返回的红字/蓝字文本拆成 {file,line,rule,level,msg} 行。"""
    rows = []
    for raw, level in ((result_text, err_level), (warn_text, warn_level)):
        if not raw or not isinstance(raw, str):
            continue
        for line in raw.split("\n"):
            line = line.strip()
            if not line or line == "存在问题:":
                continue
            rows.append(
                {
                    "file": file_name,
                    "line": None,
                    "rule": rule_label(line),
                    "level": level,
                    "msg": line,
                }
            )
    return rows


def text_to_messages(result_text, warn_text, err_level="err", warn_level="warn"):
    """与 text_to_rows 类似，但用于卡片内的纯文本提示（不含 file 列）。"""
    msgs = []
    for raw, level in ((result_text, err_level), (warn_text, warn_level)):
        if not raw or not isinstance(raw, str):
            continue
        for line in raw.split("\n"):
            line = line.strip()
            if line and line != "存在问题:":
                msgs.append({"level": level, "msg": line})
    return msgs


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
