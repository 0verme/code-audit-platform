import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.modules.audit.checks.ai_service import call_sql_llm


class LocalLlmAiServiceTests(unittest.TestCase):
    def test_returns_none_when_model_is_not_configured(self):
        with patch.dict(os.environ, {"LOCAL_LLM_BASE_URL": "", "LOCAL_LLM_MODEL": ""}, clear=False):
            self.assertIsNone(call_sql_llm("does-not-need-to-exist.py"))

    def test_calls_openai_compatible_endpoint_and_normalises_json(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job.py"
            source.write_text("print('hello')", encoding="utf-8")
            response = MagicMock()
            response.read.return_value = json.dumps({
                "choices": [{"message": {"content": json.dumps({
                    "summary": "发现风险",
                    "findings": [{"severity": "warn", "title": "异常处理", "line_start": 1, "suggestion": "记录并处理异常"}],
                }, ensure_ascii=False)}}],
            }, ensure_ascii=False).encode("utf-8")
            response.__enter__.return_value = response

            with patch.dict(os.environ, {
                "LOCAL_LLM_BASE_URL": "http://llm.internal/v1",
                "LOCAL_LLM_MODEL": "internal-model",
                "LOCAL_LLM_TIMEOUT_SECONDS": "10",
            }, clear=False), patch("urllib.request.urlopen", return_value=response) as urlopen:
                result = call_sql_llm(str(source))

            self.assertEqual(result["summary"], "发现风险")
            self.assertEqual(result["findings"][0]["sev"], "warn")
            self.assertEqual(result["findings"][0]["title"], "异常处理")
            request = urlopen.call_args.args[0]
            self.assertEqual(request.full_url, "http://llm.internal/v1/chat/completions")
            self.assertEqual(json.loads(request.data.decode("utf-8"))["model"], "internal-model")

    def test_invalid_model_response_degrades_to_none(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job.sql"
            source.write_text("select 1", encoding="utf-8")
            response = MagicMock()
            response.read.return_value = b'{"choices":[{"message":{"content":"not json"}}]}'
            response.__enter__.return_value = response
            with patch.dict(os.environ, {"LOCAL_LLM_BASE_URL": "http://llm/v1", "LOCAL_LLM_MODEL": "m"}, clear=False), patch("urllib.request.urlopen", return_value=response):
                self.assertIsNone(call_sql_llm(str(source)))


if __name__ == "__main__":
    unittest.main()
