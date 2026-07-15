import sys
import subprocess
import unittest
from pathlib import Path
from urllib.parse import quote
from unittest.mock import Mock, patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.checks import svn_service  # noqa: E402


class SvnLogRedactionTests(unittest.TestCase):
    password = "sp ace'@:/&中文-" + "x" * 128
    url_secret = "url secret@:/&中文"

    def _config(self):
        return {
            "username": "audit-user",
            "password": self.password,
            "timeout": 120,
        }

    def _assert_no_secret(self, *values):
        rendered = repr(values)
        self.assertNotIn(self.password, rendered)
        self.assertNotIn(self.url_secret, rendered)

    def test_sanitize_command_redacts_split_and_inline_password_without_mutation(self):
        original = ["svn", "info", "--password", self.password, "--username", "audit-user"]
        safe = svn_service.sanitize_svn_command_for_log(tuple(original))

        self.assertEqual(original[3], self.password)
        self.assertEqual(safe, ["svn", "info", "--password", "***", "--username", "audit-user"])

        inline = ["svn", f"--password={self.password}"]
        safe_inline = svn_service.sanitize_svn_command_for_log(inline)
        self.assertEqual(inline[1], f"--password={self.password}")
        self.assertEqual(safe_inline[1], "--password=***")
        self._assert_no_secret(safe, safe_inline)

    def test_sanitize_url_redacts_userinfo_and_query_secrets(self):
        encoded_secret = quote(self.url_secret, safe="")
        safe = svn_service.sanitize_svn_command_for_log([
            "svn",
            f"https://user:{encoded_secret}@example.com/repo/path?token={encoded_secret}&visible=yes",
            f"https://example.com/repo?password={encoded_secret}",
            f"https://example.com/repo?access_token={encoded_secret}",
            "C:\\工作目录\\repo",
            "file:///C:/工作目录/repo",
        ])

        self.assertIn("https://user:***@example.com/repo/path?token=***&visible=yes", safe)
        self.assertIn("https://example.com/repo?password=***", safe)
        self.assertIn("https://example.com/repo?access_token=***", safe)
        self.assertIn("C:\\工作目录\\repo", safe)
        self.assertIn("file:///C:/工作目录/repo", safe)
        self._assert_no_secret(safe)

    def test_run_uses_original_command_and_safe_success_logs(self):
        result = Mock(returncode=0, stdout=b"ok", stderr=b"")
        with patch.object(svn_service.subprocess, "run", return_value=result) as run, \
                patch.object(svn_service, "log_task_event") as task_log, \
                patch.object(svn_service, "log_warning_event") as warning_log:
            svn_service.run_svn_text(self._config(), "info", f"https://u:{self.url_secret}@example.com/repo")

        executed = run.call_args.args[0]
        self.assertIn(self.password, executed)
        self.assertTrue(any(self.url_secret in item for item in executed))
        self.assertNotEqual(executed, task_log.call_args_list[0].kwargs["command"])
        self._assert_no_secret(task_log.call_args_list, warning_log.call_args_list)

    def test_nonzero_and_slow_logs_redact_command_and_output(self):
        result = Mock(returncode=1, stdout=self.password.encode(), stderr=self.password.encode())
        with patch.object(svn_service.subprocess, "run", return_value=result), \
                patch.object(svn_service, "time") as clock, \
                patch.object(svn_service, "log_task_event") as task_log, \
                patch.object(svn_service, "log_warning_event") as warning_log:
            clock.time.side_effect = [100.0, 111.0]
            svn_service.run_svn_text(self._config(), "info")

        self.assertEqual(task_log.call_count, 2)
        self.assertEqual(warning_log.call_count, 2)
        self._assert_no_secret(task_log.call_args_list, warning_log.call_args_list)

    def test_timeout_and_exception_logs_redact_command(self):
        command = svn_service.build_svn_command(self._config(), "info")
        timeout = subprocess.TimeoutExpired(command, 120, output=self.password.encode(), stderr=self.password.encode())
        for raised in (timeout, RuntimeError(f"failed with {self.password}")):
            with self.subTest(exception=type(raised).__name__), \
                    patch.object(svn_service.subprocess, "run", side_effect=raised), \
                    patch.object(svn_service, "log_exception_event") as exception_log:
                with self.assertRaises(type(raised)):
                    svn_service.run_svn_text(self._config(), "info")
            self._assert_no_secret(exception_log.call_args_list)


if __name__ == "__main__":
    unittest.main()
