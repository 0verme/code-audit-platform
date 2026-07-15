import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.profiles import DatabaseProfile  # noqa: E402
from app.db.metadata.compat import gaussdb, postgres, router  # noqa: E402


def profile(name: str, db_type: str) -> DatabaseProfile:
    return DatabaseProfile(
        name=name,
        type=db_type,
        config={
            "type": db_type,
            "host": "127.0.0.1",
            "port": 5432,
            "database": "demo",
            "username": "tester",
            "password": "secret",
            "schema": "dwp",
        },
    )


class SharedDbRouterTests(unittest.TestCase):
    def setUp(self):
        router._module_for_type.cache_clear()

    def tearDown(self):
        router._module_for_type.cache_clear()

    def test_get_backend_returns_resolved_profile_type(self):
        with patch.object(router, "_resolve", return_value=profile("local_pg", "postgresql")):
            self.assertEqual(router.get_backend("local_pg"), "postgresql")

        with patch.object(router, "_resolve", return_value=profile("local_dws", "dws")):
            self.assertEqual(router.get_backend("local_dws"), "dws")

    def test_module_for_type_matches_current_backend_modules(self):
        self.assertIs(router._module_for_type("postgresql"), postgres)
        self.assertIs(router._module_for_type("dws"), gaussdb)

    def test_module_for_type_rejects_unknown_backend_type(self):
        with self.assertRaisesRegex(RuntimeError, "Unsupported database type in router: oracle"):
            router._module_for_type("oracle")

    def test_select_sql_with_profile_routes_postgresql_profile_and_preserves_profile_name(self):
        resolved = profile("local_pg", "postgresql")
        backend = types.SimpleNamespace(select_sql_with_profile=lambda profile_name, sql: (profile_name, sql))

        with patch.object(router, "_resolve", return_value=resolved) as resolve_mock:
            with patch.object(router, "_impl", return_value=backend) as impl_mock:
                result = router.select_sql_with_profile("local_pg", "select 1")

        self.assertEqual(result, ("local_pg", "select 1"))
        self.assertEqual(resolve_mock.call_args_list, [unittest.mock.call("local_pg")])
        self.assertEqual(impl_mock.call_args_list, [unittest.mock.call("local_pg")])

    def test_select_sql_with_profile_uses_default_resolved_profile_when_argument_is_none(self):
        resolved = profile("czcb", "postgresql")
        backend = types.SimpleNamespace(select_sql_with_profile=lambda profile_name, sql: {"profile": profile_name, "sql": sql})

        with patch.object(router, "_resolve", return_value=resolved) as resolve_mock:
            with patch.object(router, "_impl", return_value=backend):
                result = router.select_sql_with_profile(None, "select 2")

        self.assertEqual(result, {"profile": "czcb", "sql": "select 2"})
        self.assertEqual(resolve_mock.call_args_list, [unittest.mock.call(None)])

    def test_select_sql_with_profile_routes_dws_profile(self):
        resolved = profile("local_dws", "dws")
        backend = types.SimpleNamespace(select_sql_with_profile=lambda profile_name, sql: [profile_name, sql])

        with patch.object(router, "_resolve", return_value=resolved):
            with patch.object(router, "_impl", return_value=backend):
                self.assertEqual(router.select_sql_with_profile("local_dws", "select 3"), ["local_dws", "select 3"])

    def test_run_sql_with_profile_routes_to_backend_executor_with_resolved_name(self):
        resolved = profile("local_pg", "postgresql")
        backend = types.SimpleNamespace(run_sql_with_profile=lambda profile_name, sql: (profile_name, sql, True))

        with patch.object(router, "_resolve", return_value=resolved) as resolve_mock:
            with patch.object(router, "_impl", return_value=backend) as impl_mock:
                result = router.run_sql_with_profile("local_pg", "update demo set ok = 1")

        self.assertEqual(result, ("local_pg", "update demo set ok = 1", True))
        self.assertEqual(resolve_mock.call_args_list, [unittest.mock.call("local_pg")])
        self.assertEqual(impl_mock.call_args_list, [unittest.mock.call("local_pg")])


if __name__ == "__main__":
    unittest.main()
