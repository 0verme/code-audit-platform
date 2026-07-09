from __future__ import annotations


def load_result_table_annotations(*, safe, public_data, normalize_table):
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

    def build_sys_map():
        mapping = {}
        for row in (public_data.all_result_table_sys_names() or []):
            if not row or len(row) < 2 or row[0] is None or row[1] is None:
                continue
            table = normalize_table(row[0])
            sys_name = str(row[1]).strip()
            if table and sys_name:
                mapping.setdefault(table, [])
                if sys_name not in mapping[table]:
                    mapping[table].append(sys_name)
        return mapping

    sys_name_map = safe("结果表源系统(all_result_table_sys_names)", build_sys_map, {})
    return disabled, sys_name_map


def annotate_table(name, disabled, sys_name_map, *, normalize_table, highlight_result_source_systems):
    normalized = normalize_table(name)
    sys_names = sys_name_map.get(normalized, [])
    is_disabled = normalized in disabled
    highlight_targets = {item.strip().upper() for item in highlight_result_source_systems}
    highlight = is_disabled or any(sys_name.strip().upper() in highlight_targets for sys_name in sys_names)
    return {"name": normalized, "disabled": is_disabled, "sysNames": sys_names, "highlight": highlight}
