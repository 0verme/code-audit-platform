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

from app.db.profiles import (  # noqa: E402
    CONFIG_PATH_ENV,
    DEFAULT_CONFIG_PATH,
    LEGACY_CONFIG_PATH_ENV,
    ProfileConfigError,
    load_database_config,
    resolve_config_path,
    resolve_profile,
    resolve_metadata_profile,
)
from app.db.tables import qualified_table_name  # noqa: E402


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

    def test_dws_legacy_settings_build_jdbc_url_and_timeouts(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp)
            profile = resolve_profile("local_dws", config_path=config_path)
        self.assertEqual(profile.config["user"], "change_me")
        self.assertEqual(
            profile.config["jdbc_url"],
            "jdbc:gaussdb://127.0.0.1:8000/code_audit?currentSchema=dwp&loginTimeout=30&connectTimeout=30000&socketTimeout=120000",
        )
        self.assertEqual(profile.config["jar_path"], str(BACKEND_DIR / "resources" / "jars" / "gaussdb200.jar"))

    def test_dws_jdbc_url_preserves_explicit_timeout_parameters(self):
        content = """
default_profile: dws
profiles:
  dws:
    type: dws
    jdbc_url: jdbc:gaussdb://db.example:8000/audit?currentSchema=custom&socketTimeout=99
    user: demo
    password: demo
    connect_timeout: 4
    socket_timeout: 8
"""
        with tempfile.TemporaryDirectory() as tmp:
            profile = resolve_profile(config_path=self.write_config(tmp, content))
        self.assertIn("loginTimeout=4", profile.config["jdbc_url"])
        self.assertIn("connectTimeout=4000", profile.config["jdbc_url"])
        self.assertIn("socketTimeout=99", profile.config["jdbc_url"])

    def test_explicit_profile_argument_overrides_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp)
            profile = resolve_profile("local_dws", config_path=config_path)
        self.assertEqual(profile.name, "local_dws")

    def test_metadata_profile_defaults_to_runtime_when_not_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp)
            metadata = resolve_metadata_profile(config_path=config_path)
        # No metadata_profile key → falls back to default_profile (local_pg)
        self.assertEqual(metadata.name, "local_pg")

    def test_metadata_profile_from_yaml_key(self):
        content = """
default_profile: local_dws
metadata_profile: local_pg
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
  inner_dws:
    type: dws
    host: 127.0.0.1
    port: 8000
    database: code_audit
    username: change_me
    password: change_me
    schema: dwp
"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp, content)
            runtime = resolve_profile(config_path=config_path)
            metadata = resolve_metadata_profile(config_path=config_path)
        self.assertEqual((runtime.name, runtime.type), ("local_dws", "dws"))
        self.assertEqual((metadata.name, metadata.type), ("local_pg", "postgresql"))

    def test_deployment_mode_requires_inner_dws(self):
        content = """
default_profile: inner_dws
deployment_mode: production
profiles:
  local_pg:
    type: postgresql
    host: 127.0.0.1
    port: 5432
    database: code_audit
    username: change_me
    password: change_me
    schema: dwp
  inner_dws:
    type: dws
    host: 127.0.0.1
    port: 8000
    database: code_audit
    username: change_me
    password: change_me
    schema: dwp
"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp, content)
            runtime = resolve_profile(config_path=config_path)
            metadata = resolve_metadata_profile(config_path=config_path)
        self.assertEqual((runtime.name, runtime.type), ("inner_dws", "dws"))
        self.assertEqual((metadata.name, metadata.type), ("inner_dws", "dws"))

    def test_deployment_mode_with_metadata_override(self):
        content = """
default_profile: inner_dws
metadata_profile: local_pg
deployment_mode: production
profiles:
  local_pg:
    type: postgresql
    host: 127.0.0.1
    port: 5432
    database: code_audit
    username: change_me
    password: change_me
    schema: dwp
  inner_dws:
    type: dws
    host: 127.0.0.1
    port: 8000
    database: code_audit
    username: change_me
    password: change_me
    schema: dwp
"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp, content)
            runtime = resolve_profile(config_path=config_path)
            metadata = resolve_metadata_profile(config_path=config_path)
        self.assertEqual((runtime.name, runtime.type), ("inner_dws", "dws"))
        self.assertEqual((metadata.name, metadata.type), ("local_pg", "postgresql"))

    def test_deployment_mode_rejects_non_inner_dws_runtime(self):
        content = """
default_profile: local_pg
deployment_mode: inner
profiles:
  local_pg:
    type: postgresql
    host: 127.0.0.1
    port: 5432
    database: code_audit
    username: change_me
    password: change_me
    schema: dwp
  inner_dws:
    type: dws
    host: 127.0.0.1
    port: 8000
    database: code_audit
    username: change_me
    password: change_me
    schema: dwp
"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp, content)
            with self.assertRaisesRegex(ProfileConfigError, "requires database profile 'inner_dws'"):
                resolve_profile(config_path=config_path)

    def test_metadata_validation_does_not_bypass_runtime_deployment_check(self):
        content = """
default_profile: local_pg
metadata_profile: inner_dws
deployment_mode: inner
profiles:
  local_pg:
    type: postgresql
    host: 127.0.0.1
    port: 5432
    database: code_audit
    username: change_me
    password: change_me
    schema: dwp
  inner_dws:
    type: dws
    host: 127.0.0.1
    port: 8000
    database: code_audit
    username: change_me
    password: change_me
    schema: dwp
"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp, content)
            with self.assertRaisesRegex(ProfileConfigError, "requires database profile 'inner_dws'"):
                resolve_metadata_profile(config_path=config_path)

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
        content = """
default_profile: nonexistent
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
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self.write_config(tmp, content)
            with self.assertRaisesRegex(
                ProfileConfigError,
                r"Database profile not found: nonexistent \(source: default_profile; available: local_dws, local_pg; supported types: \[postgresql, dws\]\)",
            ):
                resolve_profile(config_path=config_path)

    def test_missing_default_config_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = Path(tmp) / "missing.yaml"
            with patch("app.db.profiles.DEFAULT_CONFIG_PATH", missing_path):
                with patch.dict(
                    os.environ,
                    {CONFIG_PATH_ENV: "", LEGACY_CONFIG_PATH_ENV: ""},
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


if __name__ == "__main__":
    unittest.main()
