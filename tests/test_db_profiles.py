import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db.profiles import CONFIG_PATH_ENV, PROFILE_ENV, ProfileConfigError, resolve_profile  # noqa: E402
from db.tables import qualified_table_name  # noqa: E402


CONFIG_TEXT = """
default_profile: sqlite
profiles:
  sqlite:
    type: sqlite
    path: backend/data/app.db
  local_pg:
    type: postgresql
    host: 127.0.0.1
    port: 5432
    database: code_audit
    username: change_me
    password: change_me
    schema: dwp
  local_dws:
    type: dws
    host: 127.0.0.1
    port: 8000
    database: code_audit
    username: change_me
    password: change_me
    schema: dwp
"""


class DatabaseProfileTests(unittest.TestCase):
    def write_config(self, directory: str) -> Path:
        path = Path(directory) / "database.yaml"
        path.write_text(CONFIG_TEXT, encoding="utf-8")
        return path

    def test_default_profile_uses_unified_postgres_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "database.yaml"
            config_path.write_text(
                """
backend: postgres
postgres:
  host: 127.0.0.1
  port: 5432
  dbname: code_audit_test
  user: tester
  password: secret
  schema: dwp
""",
                encoding="utf-8",
            )
            with patch("db.profiles.DEFAULT_CONFIG_PATH", config_path):
                with patch.dict(os.environ, {CONFIG_PATH_ENV: "", PROFILE_ENV: ""}, clear=False):
                    profile = resolve_profile()
        self.assertEqual(profile.name, "postgres")
        self.assertEqual(profile.type, "postgresql")
        self.assertEqual(profile.config["database"], "code_audit_test")
        self.assertEqual(profile.config["schema"], "dwp")
        self.assertEqual(profile.config["table_prefix"], "p_audit_")

    def test_unified_postgres_config_takes_precedence_over_gauss_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "database.yaml"
            config_path.write_text(
                """
backend: postgres
postgres:
  host: 127.0.0.1
  port: 5432
  dbname: code_audit_test
  user: tester
  password: secret
  schema: dwp
profiles:
  czcb:
    jdbc_url: jdbc:gaussdb://127.0.0.1:25308/czcb
    user: gauss
    password: secret
""",
                encoding="utf-8",
            )
            with patch("db.profiles.DEFAULT_CONFIG_PATH", config_path):
                with patch.dict(os.environ, {CONFIG_PATH_ENV: "", PROFILE_ENV: ""}, clear=False):
                    profile = resolve_profile()
        self.assertEqual(profile.name, "postgres")
        self.assertEqual(profile.type, "postgresql")
        self.assertEqual(profile.config["database"], "code_audit_test")

    def test_missing_default_config_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = Path(tmp) / "missing.yaml"
            with patch("db.profiles.DEFAULT_CONFIG_PATH", missing_path):
                with patch.dict(os.environ, {CONFIG_PATH_ENV: "", PROFILE_ENV: ""}, clear=False):
                    with self.assertRaisesRegex(ProfileConfigError, "does not exist"):
                        resolve_profile()

    def test_non_postgres_backend_does_not_enable_default_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "database.yaml"
            config_path.write_text("backend: gaussdb\n", encoding="utf-8")
            with patch("db.profiles.DEFAULT_CONFIG_PATH", config_path):
                with patch.dict(os.environ, {CONFIG_PATH_ENV: "", PROFILE_ENV: ""}, clear=False):
                    with self.assertRaisesRegex(ProfileConfigError, "must define profiles or set backend: postgres"):
                        resolve_profile()

    def test_loads_sqlite_profile_from_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp)
            profile = resolve_profile("sqlite", config_path=config_path)
        self.assertTrue(profile.is_sqlite)
        self.assertEqual(profile.config["database"], profile.config["path"])

    def test_loads_postgresql_profile_from_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp)
            profile = resolve_profile("local_pg", config_path=config_path)
        self.assertTrue(profile.is_postgresql)
        self.assertEqual(profile.config["host"], "127.0.0.1")
        self.assertEqual(profile.config["port"], 5432)
        self.assertEqual(qualified_table_name("audit_tasks", profile), "dwp.p_audit_run")

    def test_sqlite_profile_resolves_prefixed_table_names_without_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp)
            profile = resolve_profile("sqlite", config_path=config_path)
        self.assertEqual(qualified_table_name("audit_tasks", profile), "p_audit_run")

    def test_loads_dws_profile_from_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp)
            profile = resolve_profile("local_dws", config_path=config_path)
        self.assertTrue(profile.is_dws)
        self.assertEqual(profile.config["schema"], "dwp")

    def test_environment_profile_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp)
            env = {PROFILE_ENV: "local_dws"}
            with patch.dict(os.environ, env, clear=False):
                profile = resolve_profile(config_path=config_path)
        self.assertEqual(profile.name, "local_dws")
        self.assertTrue(profile.is_dws)

    def test_missing_explicit_config_has_friendly_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = Path(tmp) / "missing.yaml"
            with self.assertRaisesRegex(ProfileConfigError, "does not exist"):
                resolve_profile(config_path=missing_path)


if __name__ == "__main__":
    unittest.main()
