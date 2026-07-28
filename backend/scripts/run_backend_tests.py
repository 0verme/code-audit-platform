"""Run the complete backend suite against isolated, offline test settings."""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
TEST_CONFIG = PROJECT_ROOT / "tests" / "fixtures" / "database.yaml"


def main() -> int:
    sys.path.insert(0, str(BACKEND_DIR))
    os.environ["AUDIT_DATABASE_CONFIG"] = str(TEST_CONFIG)
    for name in (
        "CODE_AUDIT_DB_CONFIG_PATH",
        "FINE_REPORT_PREVIEW_URL",
        "LOCAL_LLM_BASE_URL",
        "SVN_USERNAME",
        "SVN_PASSWORD",
    ):
        os.environ.pop(name, None)

    with tempfile.TemporaryDirectory(prefix="code-audit-tests-") as temp_dir:
        from app.db.metadata.compat import postgres as metadata_postgres
        from app.services import health_service

        def reject_metadata_network(_profile):
            raise RuntimeError("network access is disabled by the backend test runner")

        @contextmanager
        def isolated_health_connection(_profile):
            connection = sqlite3.connect(Path(temp_dir) / "health.sqlite3")
            try:
                yield connection
            finally:
                connection.close()

        metadata_postgres.connect_postgresql = reject_metadata_network
        health_service.connect = isolated_health_connection
        root_suite = unittest.defaultTestLoader.discover(
            str(PROJECT_ROOT / "tests"),
            pattern="test_*.py",
            top_level_dir=str(PROJECT_ROOT / "tests"),
        )
        backend_suite = unittest.defaultTestLoader.discover(
            str(BACKEND_DIR / "tests"),
            pattern="test_*.py",
            top_level_dir=str(BACKEND_DIR),
        )
        suite = unittest.TestSuite((root_suite, backend_suite))
        return 0 if unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
