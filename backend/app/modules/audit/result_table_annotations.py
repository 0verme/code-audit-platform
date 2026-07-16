from __future__ import annotations


def build_result_table_sys_name_map(rows, *, normalize_table):
    """Normalize result-table source-system rows into the report annotation shape."""
    mapping = {}
    for row in rows or []:
        if not row or len(row) < 2 or row[0] is None or row[1] is None:
            continue
        table = normalize_table(row[0])
        sys_name = str(row[1]).strip()
        if table and sys_name:
            mapping.setdefault(table, [])
            if sys_name not in mapping[table]:
                mapping[table].append(sys_name)
    return mapping


def load_result_table_annotations(*, safe, public_data, normalize_table, sys_name_rows=None, disabled_tables=None):
    if disabled_tables is None:
        disabled = set(
            safe(
                "禁用结果表(all_disabled_result_tables)",
                lambda: {
                    normalize_table(row[0])
                    for row in (public_data.all_disabled_result_tables() or [])
                    if row and row[0]
                },
                set(),
            )
        )
    else:
        disabled = {normalize_table(table) for table in disabled_tables if normalize_table(table)}

    if sys_name_rows is None:
        sys_name_map = safe(
            "结果表源系统(all_result_table_sys_names)",
            lambda: build_result_table_sys_name_map(
                public_data.all_result_table_sys_names(), normalize_table=normalize_table
            ),
            {},
        )
    else:
        sys_name_map = build_result_table_sys_name_map(sys_name_rows, normalize_table=normalize_table)
    return disabled, sys_name_map


def annotate_table(name, disabled, sys_name_map, *, normalize_table, highlight_result_source_systems):
    normalized = normalize_table(name)
    sys_names = sys_name_map.get(normalized, [])
    is_disabled = normalized in disabled
    highlight_targets = {item.strip().upper() for item in highlight_result_source_systems}
    highlight = is_disabled or any(sys_name.strip().upper() in highlight_targets for sys_name in sys_names)
    return {"name": normalized, "disabled": is_disabled, "sysNames": sys_names, "highlight": highlight}
