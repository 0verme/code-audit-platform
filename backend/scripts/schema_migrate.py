from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.connection import connect  # noqa: E402
from app.db.profiles import get_active_profile  # noqa: E402
from app.migrations import MigrationRunner  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply or inspect audit database migrations")
    parser.add_argument("command", choices=("status", "apply"))
    args = parser.parse_args()
    profile = get_active_profile()
    with connect(profile) as connection:
        runner = MigrationRunner(connection, profile.type, BACKEND_DIR / "migrations", profile)
        if args.command == "apply":
            print("Applied:", ", ".join(runner.apply()) or "none")
        else:
            state = runner.status(create_ledger=False)
            print("Applied:", ", ".join(state.applied) or "none")
            print("Pending:", ", ".join(item.version for item in state.pending) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
