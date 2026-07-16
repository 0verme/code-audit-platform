import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.metadata.compat import gaussdb  # noqa: E402
from app.db.profiles import DatabaseProfile  # noqa: E402


def dws_profile():
    return DatabaseProfile("inner_dws", "dws", {"type": "dws"})


class FakeCursor:
    def __init__(self, rows, execute_error=None):
        self.rows = rows
        self.execute_error = execute_error
        self.executed = []
        self.closed = False

    def execute(self, sql):
        self.executed.append(sql)
        if self.execute_error is not None:
            raise self.execute_error

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor_factory):
        self.cursor_factory = cursor_factory
        self.cursors = []
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        cursor = self.cursor_factory()
        self.cursors.append(cursor)
        return cursor

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class DwsMetadataConnectionPoolTests(unittest.TestCase):
    def setUp(self):
        gaussdb.close_metadata_connections()

    def tearDown(self):
        gaussdb.close_metadata_connections()

    def test_sequential_metadata_queries_reuse_one_jdbc_connection(self):
        connection = FakeConnection(lambda: FakeCursor([("ok",)]))
        with (
            patch.object(gaussdb, "get_db_profile", return_value=dws_profile()),
            patch.object(gaussdb, "connect_dws", return_value=connection) as connect_dws,
        ):
            self.assertEqual(gaussdb.fetch_all("inner_dws", "select first"), [("ok",)])
            self.assertEqual(gaussdb.fetch_all("inner_dws", "select second"), [("ok",)])

        connect_dws.assert_called_once()
        self.assertEqual([cursor.executed for cursor in connection.cursors], [["select first"], ["select second"]])
        self.assertEqual(connection.rollbacks, 2)
        self.assertFalse(connection.closed)

    def test_failed_query_discards_connection_before_next_query(self):
        failed = FakeConnection(lambda: FakeCursor([], execute_error=RuntimeError("query failed")))
        healthy = FakeConnection(lambda: FakeCursor([("ok",)]))
        with (
            patch.object(gaussdb, "get_db_profile", return_value=dws_profile()),
            patch.object(gaussdb, "connect_dws", side_effect=[failed, healthy]) as connect_dws,
        ):
            self.assertIsNone(gaussdb.fetch_all("inner_dws", "select broken"))
            self.assertEqual(gaussdb.fetch_all("inner_dws", "select healthy"), [("ok",)])

        self.assertEqual(connect_dws.call_count, 2)
        self.assertTrue(failed.closed)
        self.assertFalse(healthy.closed)

    def test_stale_pooled_connection_retries_once_with_new_connection(self):
        cursors = iter([
            FakeCursor([("first",)]),
            FakeCursor([], execute_error=RuntimeError("stale connection")),
        ])
        stale = FakeConnection(lambda: next(cursors))
        healthy = FakeConnection(lambda: FakeCursor([("second",)]))
        with (
            patch.object(gaussdb, "get_db_profile", return_value=dws_profile()),
            patch.object(gaussdb, "connect_dws", side_effect=[stale, healthy]) as connect_dws,
        ):
            self.assertEqual(gaussdb.fetch_all("inner_dws", "select first"), [("first",)])
            self.assertEqual(gaussdb.fetch_all("inner_dws", "select second"), [("second",)])

        self.assertEqual(connect_dws.call_count, 2)
        self.assertTrue(stale.closed)
        self.assertFalse(healthy.closed)

    def test_pool_shutdown_closes_idle_connections(self):
        connection = FakeConnection(lambda: FakeCursor([]))
        with (
            patch.object(gaussdb, "get_db_profile", return_value=dws_profile()),
            patch.object(gaussdb, "connect_dws", return_value=connection),
        ):
            gaussdb.fetch_all("inner_dws", "select 1")

        gaussdb.close_metadata_connections()

        self.assertTrue(connection.closed)


if __name__ == "__main__":
    unittest.main()
