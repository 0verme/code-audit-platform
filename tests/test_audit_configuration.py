import unittest
from unittest.mock import patch

from app import create_app


class AuditConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app(recover_tasks=False).test_client()

    @patch("app.routes.audit_configuration.load_svn_config")
    @patch("app.routes.audit_configuration.get_audit_rules")
    def test_workflows_include_safe_svn_source_display_rules(self, get_rules, load_svn):
        get_rules.return_value = {
            "workflows": {"default": "hcyt", "definitions": [{"id": "hcyt"}]},
            "source_display_rules": [
                {"sourceType": "local", "prefix": "C:/workspace/", "replacement": "…/"},
            ],
        }
        load_svn.return_value = {
            "defaults": {"username": "user", "password": "secret"},
            "projects": {
                "hcyt": {
                    "trunk_url": "svn://svn.example.com/hcyt/branches/",
                    "username": "user",
                    "password": "secret",
                },
                "duplicate": {"trunk_url": "SVN://SVN.EXAMPLE.COM/HCYT/BRANCHES"},
                "missing": {"marker": "nups/"},
            },
        }

        response = self.client.get("/api/audit-configuration/workflows")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["default"], "hcyt")
        self.assertEqual(payload["definitions"], [{"id": "hcyt"}])
        self.assertEqual(payload["sourceDisplayRules"], [
            {"sourceType": "local", "prefix": "C:/workspace/", "replacement": "…/"},
            {
                "sourceType": "svn",
                "prefix": "svn://svn.example.com/hcyt/branches/",
                "replacement": "…/",
            },
        ])
        self.assertNotIn("username", response.get_data(as_text=True))
        self.assertNotIn("password", response.get_data(as_text=True))
        self.assertNotIn("secret", response.get_data(as_text=True))

    @patch("app.routes.audit_configuration.load_svn_config", side_effect=FileNotFoundError)
    @patch("app.routes.audit_configuration.get_audit_rules")
    def test_workflows_remain_available_without_svn_config(self, get_rules, _load_svn):
        get_rules.return_value = {
            "workflows": {"default": "hcyt", "definitions": []},
            "source_display_rules": [],
        }

        response = self.client.get("/api/audit-configuration/workflows")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["sourceDisplayRules"], [])


if __name__ == "__main__":
    unittest.main()
