from __future__ import annotations

from collections.abc import Callable


def sync_hcyt_legacy_results(save_category_rows: Callable[[dict[str, list[dict]]], None], grouped_rows):
    save_category_rows(grouped_rows)


def save_hcyt_legacy_audit_results(save_category_rows: Callable[[dict[str, list[dict]]], None], grouped_rows):
    sync_hcyt_legacy_results(save_category_rows, grouped_rows)
