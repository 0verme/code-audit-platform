import importlib
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Lock
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.modules.audit.engine as audit_engine  # noqa: E402
from app.db import connection as db_connection  # noqa: E402
from app.db.schema import init_db  # noqa: E402
from app.db.runtime_store import create_audit_task as real_create_audit_task  # noqa: E402
from app.services.audit_task_service import create_task  # noqa: E402


PAYLOAD = {
    "sourceRef": "svn://example.com/repos/branches/demo-hcyt",
    "sourceType": "svn",
    "workflow": "hcyt",
    "ai_enabled": True,
    "debug_enabled": False,
}


class AuditTaskIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.old_db_path = db_connection.DB_PATH
        db_connection.DB_PATH = Path(self.tmp.name) / "app.db"
        init_db()

    def tearDown(self):
        db_connection.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    def test_both_create_endpoints_replay_the_same_task(self):
        app_module = importlib.import_module("app")
        start_task_calls = []
        with patch.object(audit_engine, "start_task", lambda *args: start_task_calls.append(args)):
            client = app_module.create_app().test_client()
            first = client.post(
                "/api/audit-runs",
                json=PAYLOAD,
                headers={"Idempotency-Key": "submission-1"},
            )
            replay = client.post(
                "/api/audit-tasks",
                json=PAYLOAD,
                headers={"Idempotency-Key": "submission-1"},
            )

        self.assertEqual(first.status_code, 201)
        self.assertFalse(first.get_json()["deduplicated"])
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.get_json()["deduplicated"])
        self.assertEqual(first.get_json()["id"], replay.get_json()["id"])
        self.assertEqual(len(start_task_calls), 1)

    def test_reusing_a_key_with_different_parameters_returns_conflict(self):
        app_module = importlib.import_module("app")
        with patch.object(audit_engine, "start_task"):
            client = app_module.create_app().test_client()
            client.post(
                "/api/audit-runs",
                json=PAYLOAD,
                headers={"Idempotency-Key": "submission-2"},
            )
            response = client.post(
                "/api/audit-runs",
                json={**PAYLOAD, "debug_enabled": True},
                headers={"Idempotency-Key": "submission-2"},
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["errorCode"], "idempotency_conflict")

    def test_new_keys_and_legacy_requests_create_new_tasks(self):
        app_module = importlib.import_module("app")
        with patch.object(audit_engine, "start_task") as start_task:
            client = app_module.create_app().test_client()
            responses = [
                client.post("/api/audit-runs", json=PAYLOAD, headers={"Idempotency-Key": "submission-a"}),
                client.post("/api/audit-runs", json=PAYLOAD, headers={"Idempotency-Key": "submission-b"}),
                client.post("/api/audit-runs", json=PAYLOAD),
                client.post("/api/audit-runs", json=PAYLOAD),
            ]

        self.assertTrue(all(response.status_code == 201 for response in responses))
        self.assertEqual(len({response.get_json()["id"] for response in responses}), 4)
        self.assertEqual(start_task.call_count, 4)

    def test_concurrent_service_calls_start_only_one_task(self):
        barrier = Barrier(2)
        calls = 0
        calls_lock = Lock()

        def synchronized_insert(**kwargs):
            barrier.wait(timeout=5)
            return real_create_audit_task(**kwargs)

        def record_start(*_args):
            nonlocal calls
            with calls_lock:
                calls += 1

        with (
            patch("app.services.audit_task_service.create_audit_task", side_effect=synchronized_insert),
            patch.object(audit_engine, "start_task", side_effect=record_start),
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            futures = [
                pool.submit(create_task, PAYLOAD, client_ip="127.0.0.1", idempotency_key="submission-race")
                for _ in range(2)
            ]
            results = [future.result(timeout=10) for future in futures]

        self.assertEqual({result["id"] for result in results}, {results[0]["id"]})
        self.assertEqual(sorted(result["deduplicated"] for result in results), [False, True])
        self.assertEqual(calls, 1)

    def test_non_unique_database_errors_are_not_treated_as_idempotent_replays(self):
        with (
            patch(
                "app.services.audit_task_service.create_audit_task",
                side_effect=RuntimeError("database unavailable"),
            ),
            patch.object(audit_engine, "start_task") as start_task,
        ):
            with self.assertRaisesRegex(RuntimeError, "database unavailable"):
                create_task(
                    PAYLOAD,
                    client_ip="127.0.0.1",
                    idempotency_key="submission-db-error",
                )

        start_task.assert_not_called()


if __name__ == "__main__":
    unittest.main()
