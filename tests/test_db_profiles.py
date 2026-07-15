import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db.profiles import (  # noqa: E402
    CONFIG_PATH_ENV,
    DEFAULT_CONFIG_PATH,
    DEPLOYMENT_MODE_ENV,
    LEGACY_CONFIG_PATH_ENV,
    PROFILE_ENV,
    ProfileConfigError,
    load_database_config,
    resolve_config_path,
    resolve_profile,
)
from db.tables import qualified_table_name  # noqa: E402


CONFIG_TEXT = """
default_profile: local_pg
profiles:
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
    def write_config(self, directory: str, content: str = CONFIG_TEXT) -> Path:
        path = Path(directory) / "database.yaml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_loads_default_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp)
            profile = resolve_profile(config_path=config_path)
        self.assertEqual(profile.name, "local_pg")
        self.assertEqual(profile.type, "postgresql")
        self.assertEqual(profile.config["port"], 5432)
        self.assertEqual(qualified_table_name("audit_tasks", profile), "dwp.p_audit_run")

    def test_loads_dws_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp)
            profile = resolve_profile("local_dws", config_path=config_path)
        self.assertTrue(profile.is_dws)
        self.assertEqual(profile.config["schema"], "dwp")

    def test_environment_profile_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp)
            with patch.dict(os.environ, {PROFILE_ENV: "local_dws"}, clear=False):
                profile = resolve_profile(config_path=config_path)
        self.assertEqual(profile.name, "local_dws")

    def test_default_path_is_backend_configs_database_yaml_independent_of_cwd(self):
        expected = BACKEND_DIR / "configs" / "database.yaml"
        self.assertEqual(DEFAULT_CONFIG_PATH, expected)
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                with patch.dict(
                    os.environ,
                    {CONFIG_PATH_ENV: "", LEGACY_CONFIG_PATH_ENV: ""},
                    clear=False,
                ):
                    self.assertEqual(resolve_config_path(), expected)
            finally:
                os.chdir(original_cwd)

    def test_environment_config_override_has_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp)
            legacy_path = Path(tmp) / "legacy.yaml"
            legacy_path.write_text(CONFIG_TEXT.replace("local_pg", "legacy_pg"), encoding="utf-8")
            with patch.dict(
                os.environ,
                {CONFIG_PATH_ENV: str(config_path), LEGACY_CONFIG_PATH_ENV: str(legacy_path)},
                clear=False,
            ):
                self.assertEqual(resolve_config_path(), config_path)

    def test_legacy_environment_config_override_is_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp)
            with patch.dict(
                os.environ,
                {CONFIG_PATH_ENV: "", LEGACY_CONFIG_PATH_ENV: str(config_path)},
                clear=False,
            ):
                self.assertEqual(resolve_config_path(), config_path)

    def test_legacy_mixed_mode_is_rejected(self):
        content = """
default_profile: postgres
backend: postgres
postgres:
  host: 127.0.0.1
"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp, content)
            with self.assertRaisesRegex(ProfileConfigError, r"legacy keys backend, postgres"):
                resolve_profile(config_path=config_path)

    def test_missing_type_reports_profile_and_supported_types(self):
        content = """
default_profile: broken
profiles:
  broken:
    host: 127.0.0.1
    port: 5432
    database: code_audit
    username: demo
    password: demo
    schema: dwp
"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp, content)
            with self.assertRaisesRegex(
                ProfileConfigError,
                r"Invalid database profile 'broken': type is <missing>; supported types are \[postgresql, dws\]",
            ):
                resolve_profile(config_path=config_path)

    def test_missing_required_fields_are_reported(self):
        content = """
default_profile: broken
profiles:
  broken:
    type: postgresql
    host: 127.0.0.1
    port: 5432
    database: code_audit
    username: demo
"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp, content)
            with self.assertRaisesRegex(
                ProfileConfigError,
                r"Invalid database profile 'broken': missing required fields: profiles\.broken\.password, profiles\.broken\.schema; supported types are \[postgresql, dws\]",
            ):
                resolve_profile(config_path=config_path)

    def test_missing_profile_error_includes_source_and_available_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp)
            with patch.dict(os.environ, {PROFILE_ENV: "profiles"}, clear=False):
                with self.assertRaisesRegex(
                    ProfileConfigError,
                    r"Database profile not found: profiles \(source: CODE_AUDIT_DB_PROFILE; available: local_dws, local_pg; supported types: \[postgresql, dws\]\)",
                ):
                    resolve_profile(config_path=config_path)

    def test_missing_default_config_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = Path(tmp) / "missing.yaml"
            with patch("db.profiles.DEFAULT_CONFIG_PATH", missing_path):
                with patch.dict(
                    os.environ,
                    {CONFIG_PATH_ENV: "", LEGACY_CONFIG_PATH_ENV: "", PROFILE_ENV: ""},
                    clear=False,
                ):
                    with self.assertRaisesRegex(ProfileConfigError, rf"does not exist: {re.escape(str(missing_path))}"):
                        resolve_profile()

    def test_invalid_yaml_reports_path_and_parse_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp, "profiles: [not: valid")
            with self.assertRaisesRegex(
                ProfileConfigError, rf"Invalid database config YAML: {re.escape(str(config_path))}"
            ):
                load_database_config(config_path)

    def test_environment_values_expand_for_inner_dws(self):
        content = """
default_profile: inner_dws
profiles:
  inner_dws:
    type: dws
    host: ${AUDIT_DWS_HOST}
    port: ${AUDIT_DWS_PORT}
    database: ${AUDIT_DWS_DATABASE}
    username: ${AUDIT_DWS_USER}
    password: ${AUDIT_DWS_PASSWORD}
    schema: ${AUDIT_DWS_SCHEMA}
"""
        env = {
            "AUDIT_DWS_HOST": "dws.example.internal", "AUDIT_DWS_PORT": "8000",
            "AUDIT_DWS_DATABASE": "audit", "AUDIT_DWS_USER": "audit_app",
            "AUDIT_DWS_PASSWORD": "not-a-real-secret", "AUDIT_DWS_SCHEMA": "dwp",
        }
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp, content)
            with patch.dict(os.environ, env, clear=False):
                profile = resolve_profile(config_path=config_path)
        self.assertEqual(profile.name, "inner_dws")
        self.assertEqual(profile.config["host"], "dws.example.internal")

    def test_inner_mode_rejects_non_dws_or_non_inner_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp)
            with patch.dict(os.environ, {DEPLOYMENT_MODE_ENV: "inner"}, clear=False):
                with self.assertRaisesRegex(ProfileConfigError, "requires database profile 'inner_dws'"):
                    resolve_profile(config_path=config_path)


if __name__ == "__main__":
    unittest.main()
