import json
import unittest

from app import create_app
from app.modules.audit.rules.registry import RULES_BY_ID, rule_inventory


class RuleCatalogApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.expected_rules = json.loads(cls.app.json.dumps(rule_inventory()))

    def test_list_exposes_every_registry_entry_with_catalog_contract(self):
        response = self.client.get("/api/rules")

        self.assertEqual(response.status_code, 200)
        rules = response.get_json()
        self.assertEqual(rules, self.expected_rules)
        self.assertEqual(len(rules), 180)
        self.assertEqual(len({rule["id"] for rule in rules}), len(rules))
        self.assertEqual({rule["id"] for rule in rules}, set(RULES_BY_ID))

        required_fields = {
            "id", "workflow", "category", "title", "severity", "description",
            "rationale", "trigger_condition", "artifact", "config_keys", "implementation",
        }
        for rule in rules:
            self.assertTrue(required_fields <= rule.keys(), rule["id"])
            self.assertIsInstance(rule["config_keys"], list)
            self.assertTrue(rule["implementation"], rule["id"])
            self.assertTrue(
                all({"module", "function"} <= item.keys() for item in rule["implementation"])
            )

    def test_detail_returns_registry_projection_and_unknown_id_is_not_found(self):
        rule_id = "hcyt.ddl.temp_table_name"
        response = self.client.get(f"/api/rules/{rule_id}")

        self.assertEqual(response.status_code, 200)
        expected = next(rule for rule in self.expected_rules if rule["id"] == rule_id)
        self.assertEqual(response.get_json(), expected)

        unknown = self.client.get("/api/rules/not-a-registered-rule")
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.get_json()["error"]["code"], "NOT_FOUND")

    def test_list_filters_compose_and_keyword_matches_id_title_and_description(self):
        response = self.client.get(
            "/api/rules?workflow=HCYT&category=DDL&severity=ERR&keyword=%E4%B8%B4%E6%97%B6"
        )
        rules = response.get_json()
        expected = [
            rule for rule in self.expected_rules
            if rule["workflow"] == "hcyt"
            and rule["category"] == "ddl"
            and rule["severity"] == "err"
            and "临时" in rule["description"].casefold()
        ]
        self.assertEqual(rules, expected)
        self.assertTrue(any(rule["id"] == "hcyt.ddl.temp_table_name" for rule in rules))

        for keyword in ("hcyt.ddl.temp_table_name", "临时表名", "前缀"):
            with self.subTest(keyword=keyword):
                filtered = self.client.get(
                    "/api/rules", query_string={"keyword": keyword}
                ).get_json()
                self.assertTrue(
                    any(rule["id"] == "hcyt.ddl.temp_table_name" for rule in filtered)
                )

    def test_empty_filter_result_is_an_empty_list(self):
        response = self.client.get("/api/rules", query_string={"workflow": "missing"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])


if __name__ == "__main__":
    unittest.main()
