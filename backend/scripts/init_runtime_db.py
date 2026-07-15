"""Initialize and verify the audit platform runtime tables for the active profile."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.profiles import resolve_profile  # noqa: E402
from app.db.schema import RUNTIME_TABLES, ensure_runtime_tables  # noqa: E402
from app.db.tables import qualified_table_name  # noqa: E402
from app.db.connection import get_connection  # noqa: E402


def main() -> None:
    profile = resolve_profile()
    print(f"Initializing runtime tables: profile={profile.name} type={profile.type} schema={profile.config['schema']}")
    ensure_runtime_tables(profile)
    with get_connection(profile) as connection:
        for logical_name in RUNTIME_TABLES:
            table = qualified_table_name(logical_name, profile)
            connection.execute(f"SELECT 1 FROM {table} WHERE 1 = 0")
    print("Runtime tables verified")


if __name__ == "__main__":
    main()
