import unittest

from app import create_app


class AppFactoryTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(recover_tasks=False)

    def test_blueprints_register_all_legacy_api_rules(self):
        rules = {(rule.rule, frozenset(rule.methods or ())) for rule in self.app.url_map.iter_rules()}
        expected = {
            ("/api/health", "GET"),
            ("/api/projects", "GET"),
            ("/api/audit-tasks", "GET"),
            ("/api/audit-tasks", "POST"),
            ("/api/audit-tasks/<int:task_id>", "GET"),
            ("/api/audit-tasks/<int:task_id>/report", "GET"),
            ("/api/audit-tasks/<int:task_id>/source-file", "GET"),
            ("/api/audit-runs", "POST"),
            ("/api/audit-runs/<int:run_id>/status", "GET"),
            ("/api/audit-runs/<int:run_id>/partial-result", "GET"),
            ("/api/audit-results", "GET"),
            ("/api/fine-report/items", "GET"),
        }
        for path, method in expected:
            self.assertTrue(any(rule == path and method in methods for rule, methods in rules), (path, method))

    def test_error_responses_and_request_id_are_stable(self):
        client = self.app.test_client()
        response = client.get("/api/does-not-exist", headers={"X-Request-ID": "test-request"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"error": {"code": "NOT_FOUND", "message": "请求的资源不存在"}})
        self.assertEqual(response.headers["X-Request-ID"], "test-request")
        response = client.delete("/api/health")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.get_json()["error"]["code"], "METHOD_NOT_ALLOWED")


if __name__ == "__main__":
    unittest.main()
