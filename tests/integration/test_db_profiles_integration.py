import os
import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.profiles import ProfileConfigError, resolve_profile  # noqa: E402
from app.db.schema import RUNTIME_TABLES, initialize_schema  # noqa: E402
from app.db.sql_runner import SQLRunner  # noqa: E402


RUN_INTEGRATION = os.getenv("CODE_AUDIT_RUN_DB_INTEGRATION") == "1"
PROFILE_ENV = "CODE_AUDIT_INTEGRATION_PROFILE"


@unittest.skipUnless(RUN_INTEGRATION, "set CODE_AUDIT_RUN_DB_INTEGRATION=1 to run DB integration tests")
class DatabaseProfileIntegrationTests(unittest.TestCase):
    def setUp(self):
        profile_name = os.getenv(PROFILE_ENV)
        if not profile_name:
            raise unittest.SkipTest(f"set {PROFILE_ENV} to a test database profile")
        try:
            self.profile = resolve_profile(profile_name)
        except ProfileConfigError as exc:
            raise unittest.SkipTest(str(exc)) from exc
        database_name = str(self.profile.config.get("database") or "").lower()
        if "test" not in database_name:
            raise unittest.SkipTest("integration profile database name must contain 'test'")
        self.runner = SQLRunner(self.profile)

    def test_initialize_schema_and_query_tables(self):
        initialize_schema(self.profile)
        for table in RUNTIME_TABLES:
            row = self.runner.query_one("SELECT COUNT(*) AS count FROM " + "{{table:" + table + "}}")
            self.assertIsNotNone(row)
            self.assertIn("count", row)


if __name__ == "__main__":
    unittest.main()
