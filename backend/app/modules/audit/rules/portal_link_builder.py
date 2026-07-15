from __future__ import annotations

import os
from urllib.parse import urlencode


PORTAL_BASE_URL_ENV = "ASSET_PORTAL_BASE_URL"


def get_portal_base_url():
    return os.getenv(PORTAL_BASE_URL_ENV, "").strip()


def _build_url(path, params=None):
    base_url = get_portal_base_url().rstrip("/")
    if not base_url:
        return ""
    query = urlencode({key: value for key, value in (params or {}).items() if value})
    return f"{base_url}{path}?{query}" if query else f"{base_url}{path}"


def build_root_management_link(root_word):
    return _build_url("/root-management", {"q": root_word})


def build_data_warehouse_link(table_name):
    return _build_url("/data-warehouse", {"q": table_name})


def build_portal_link(issue):
    issue_type = str(getattr(issue, "issue_type", "") or "").upper()
    if issue_type == "ROOT_MISSING":
        return build_root_management_link(getattr(issue, "root_word", ""))
    if issue_type == "ASSET_TABLE_REVIEW":
        schema_name = getattr(issue, "schema_name", "")
        table_name = getattr(issue, "table_name", "")
        qualified_table_name = ".".join([value for value in (schema_name, table_name) if value]) or table_name
        return build_data_warehouse_link(qualified_table_name)
    return get_portal_base_url().rstrip("/")
