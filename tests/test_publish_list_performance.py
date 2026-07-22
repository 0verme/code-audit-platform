import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import publish_list_pool, publish_list_service  # noqa: E402


class FakeProfile:
    name = "publish_test"
    type = "postgresql"
    config = {"schema": "dwp"}


class FakeConnection:
    def __init__(self):
        self.closed = False
        self.rollback_count = 0
        self.close_count = 0

    def rollback(self):
        self.rollback_count += 1

    def close(self):
        self.close_count += 1
        self.closed = True


class FakeColumnRunner:
    def __init__(self):
        self.query_count = 0

    def query_all(self, _sql, _params=None):
        self.query_count += 1
        return [
            {"column_name": "taskid"},
            {"column_name": "tasktitle"},
            {"column_name": "taskstatus"},
            {"column_name": "taskdate"},
        ]


class PublishListPoolTests(unittest.TestCase):
    def setUp(self):
        publish_list_pool.close_publish_list_connections()

    def tearDown(self):
        publish_list_pool.close_publish_list_connections()

    def test_reuses_connection_and_rolls_back_before_release(self):
        connection = FakeConnection()
        with patch.object(publish_list_pool, "connect", return_value=connection) as connector:
            with publish_list_pool.publish_list_connection(FakeProfile()):
                pass
            with publish_list_pool.publish_list_connection(FakeProfile()):
                pass

        self.assertEqual(connector.call_count, 1)
        self.assertTrue(connection.autocommit)
        self.assertEqual(connection.rollback_count, 2)
        self.assertEqual(connection.close_count, 0)

    def test_discards_failed_connection(self):
        first = FakeConnection()
        second = FakeConnection()
        with patch.object(publish_list_pool, "connect", side_effect=[first, second]) as connector:
            with self.assertRaises(RuntimeError):
                with publish_list_pool.publish_list_connection(FakeProfile()):
                    raise RuntimeError("query failed")
            with publish_list_pool.publish_list_connection(FakeProfile()) as acquired:
                self.assertIs(acquired, second)

        self.assertEqual(connector.call_count, 2)
        self.assertEqual(first.close_count, 1)


class PublishListColumnCacheTests(unittest.TestCase):
    def setUp(self):
        publish_list_service.clear_publish_list_column_cache()

    def tearDown(self):
        publish_list_service.clear_publish_list_column_cache()

    def test_reuses_column_mapping(self):
        runner = FakeColumnRunner()
        profile = FakeProfile()

        first = publish_list_service._cached_columns(profile, runner, "dwp", "p_publishlist", {})
        second = publish_list_service._cached_columns(profile, runner, "dwp", "p_publishlist", {})

        self.assertEqual(first, second)
        self.assertEqual(runner.query_count, 1)

    def test_invalidates_mapping_and_retries_query_once(self):
        profile = FakeProfile()

        @contextmanager
        def fake_connection(_profile):
            yield object()

        with (
            patch.object(publish_list_service, "publish_list_connection", side_effect=fake_connection),
            patch.object(publish_list_service, "TransactionRunner", return_value=object()),
            patch.object(publish_list_service, "_cached_columns", side_effect=[{"date": "old_date", "id": "taskid"}, {"date": "taskdate", "id": "taskid"}]),
            patch.object(publish_list_service, "_query_rows", side_effect=[RuntimeError("stale column"), []]) as query_rows,
            patch.object(publish_list_service, "_invalidate_column_cache") as invalidate,
        ):
            rows = publish_list_service._load_rows(
                publish_list_service.date(2026, 7, 22), profile, "dwp", "p_publishlist", {}
            )

        self.assertEqual(rows, [])
        self.assertEqual(query_rows.call_count, 2)
        self.assertEqual(invalidate.call_count, 1)


if __name__ == "__main__":
    unittest.main()
