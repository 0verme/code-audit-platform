import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "backend" / "scripts" / "llm_sql_probe.py"
SPEC = importlib.util.spec_from_file_location("llm_sql_probe", SCRIPT_PATH)
llm_sql_probe = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(llm_sql_probe)


class LlmSqlProbeTests(unittest.TestCase):
    def test_normalize_endpoint_accepts_base_v1_and_full_urls(self):
        self.assertEqual(
            llm_sql_probe.normalize_endpoint("http://llm.internal"),
            "http://llm.internal/v1/chat/completions",
        )
        self.assertEqual(
            llm_sql_probe.normalize_endpoint("http://llm.internal/v1/"),
            "http://llm.internal/v1/chat/completions",
        )
        self.assertEqual(
            llm_sql_probe.normalize_endpoint("http://llm.internal/custom/chat/completions"),
            "http://llm.internal/custom/chat/completions",
        )

    def test_extract_json_content_accepts_plain_and_fenced_objects(self):
        value = {"summary": "ok", "findings": []}
        self.assertEqual(llm_sql_probe.extract_json_content(json.dumps(value)), value)
        self.assertEqual(
            llm_sql_probe.extract_json_content("```json\n" + json.dumps(value) + "\n```"),
            value,
        )
        self.assertIsNone(llm_sql_probe.extract_json_content("not-json"))

    def test_payload_has_no_auth_data_and_keeps_full_sql(self):
        sql = "select 1;\n" * 20_000
        payload = llm_sql_probe.build_payload(model="qwen", sql_text=sql, max_tokens=4096)
        self.assertEqual(payload["model"], "qwen")
        self.assertEqual(payload["max_tokens"], 4096)
        self.assertIn(sql, payload["messages"][1]["content"])
        self.assertNotIn("authorization", json.dumps(payload).lower())


if __name__ == "__main__":
    unittest.main()
