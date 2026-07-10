"""Deprecated compatibility path.

Real implementation lives in lineage.mapping_compat.
Do not add new logic here.
"""

from lineage.mapping_compat import *  # noqa: F401,F403
from lineage import mapping_compat as _impl

select_sql_with_profile = _impl.select_sql_with_profile
sqlite3 = _impl.sqlite3


def load_registered_result_tables(profile: str = "czcb") -> set[str]:
    return _impl.registered_tables_helpers.load_registered_result_tables(
        profile=profile,
        select_sql_with_profile=select_sql_with_profile,
    )


def filter_registered_result_nodes(nodes, result_tables=None, profile: str = "czcb"):
    return _impl.registered_tables_helpers.filter_registered_result_nodes(
        nodes=nodes,
        result_tables=result_tables,
        profile=profile,
        load_registered_result_tables_func=load_registered_result_tables,
    )


def __getattr__(name):
    return getattr(_impl, name)
