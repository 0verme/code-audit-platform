import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db.connection import connect  # noqa: E402
from db.profiles import DatabaseProfile  # noqa: E402
from db.sql_runner import SQLRunner  # noqa: E402


def profile(db_type: str = "postgresql") -> DatabaseProfile:
    return DatabaseProfile(
        f"test_{db_type}",
        db_type,
        {
            "type": db_type,
            "host": "127.0.0.1",
            "port": 5432,
            "database": "code_audit_test",
            "username": "change_me",
            "password": "change_me",
            "schema": "public",
        },
    )


class FakeCursor:
    def __init__(self):
        self.description = [("id",), ("name",)]
        self.rows = [(7, "demo")]
        self.executed = []
        self.rowcount = 1

    def execute(self, sql, params=()):
        self.executed.append((sql, params))

    def executemany(self, sql, param_sets):
        self.executed.append((sql, list(param_sets)))
        self.rowcount = len(param_sets)

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return (42,)

    def close(self):
        pass


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class SQLRunnerTests(unittest.TestCase):
    def test_mock_postgresql_connection_and_placeholder_conversion(self):
        fake = FakeConnection()
        runner = SQLRunner(profile("postgresql"), connection_factory=lambda _: fake)
        rows = runner.query_all("SELECT id, name FROM sample WHERE id = ?", (7,))
        self.assertEqual(rows, [{"id": 7, "name": "demo"}])
        self.assertEqual(fake.cursor_obj.executed[-1], ("SELECT id, name FROM sample WHERE id = %s", (7,)))

    def test_mock_dws_connection(self):
        fake = FakeConnection()
        runner = SQLRunner(profile("dws"), connection_factory=lambda _: fake)
        runner.execute("UPDATE sample SET name = ? WHERE id = ?", ("x", 7))
        self.assertEqual(fake.cursor_obj.executed[-1], ("UPDATE sample SET name = %s WHERE id = %s", ("x", 7)))
        self.assertEqual(fake.commits, 1)

    def test_insert_returning_id(self):
        fake = FakeConnection()
        runner = SQLRunner(profile("postgresql"), connection_factory=lambda _: fake)
        inserted_id = runner.execute("INSERT INTO sample (name) VALUES (?)", ("alpha",), return_id=True)
        self.assertEqual(inserted_id, 42)
        self.assertEqual(fake.cursor_obj.executed[-1][0], "INSERT INTO sample (name) VALUES (%s) RETURNING id")

    def test_execute_many_uses_converted_placeholders(self):
        fake = FakeConnection()
        runner = SQLRunner(profile("postgresql"), connection_factory=lambda _: fake)
        count = runner.execute_many("INSERT INTO sample (name) VALUES (?)", [("a",), ("b",)])
        self.assertEqual(count, 2)
        self.assertEqual(fake.cursor_obj.executed[-1][0], "INSERT INTO sample (name) VALUES (%s)")

    def test_transaction_commits(self):
        fake = FakeConnection()
        runner = SQLRunner(profile("postgresql"), connection_factory=lambda _: fake)
        with runner.transaction() as tx:
            tx.execute("UPDATE sample SET name = ? WHERE id = ?", ("x", 7))
        self.assertEqual(fake.commits, 1)
        self.assertTrue(fake.closed)

    def test_connect_uses_available_driver_for_both_types(self):
        fake_driver_connection = object()

        class FakePsycopg:
            @staticmethod
            def connect(**kwargs):
                return fake_driver_connection

        with patch("db.connection.psycopg", FakePsycopg), patch("db.connection.psycopg2", None):
            self.assertIs(connect(profile("postgresql")), fake_driver_connection)
            self.assertIs(connect(profile("dws")), fake_driver_connection)


if __name__ == "__main__":
    unittest.main()
