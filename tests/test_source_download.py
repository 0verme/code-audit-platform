import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import audit.engine as audit_engine  # noqa: E402
from audit.source_download import (  # noqa: E402
    build_source_download_url,
    resolve_source_download_path,
    source_relative_paths,
)


class SourceDownloadTests(unittest.TestCase):
    def _report(self, relative_path):
        return {"changes": [{"path": relative_path}]}

    def test_svn_task_downloads_dws_sql_from_its_export_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            export_base = Path(tmp)
            source_file = export_base / "feature-42" / "sql" / "dws.sql"
            source_file.parent.mkdir(parents=True)
            source_file.write_text("select 1", encoding="utf-8")
            result = resolve_source_download_path(
                task={"source_type": "svn", "source_ref": "svn://repo/branches/feature-42"},
                report=self._report("sql/dws.sql"),
                relative_path="sql/dws.sql",
                export_base=export_base,
            )
            self.assertEqual(result.read_text(encoding="utf-8"), "select 1")

    def test_local_task_downloads_encoded_chinese_and_space_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_file = root / "目录 空格" / "中文 dws.sql"
            source_file.parent.mkdir()
            source_file.write_text("select 中文", encoding="utf-8")
            relative = "目录 空格/中文 dws.sql"
            result = resolve_source_download_path(
                task={"source_type": "local", "source_ref": str(root)},
                report=self._report(relative),
                relative_path=relative,
                export_base=Path(tmp),
            )
            self.assertEqual(result, source_file.resolve())
            self.assertIn("%E4%B8%AD", build_source_download_url(9, relative))
            self.assertIn("%20", build_source_download_url(9, relative))

    def test_missing_source_file_returns_not_found_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                resolve_source_download_path(
                    task={"source_type": "local", "source_ref": tmp},
                    report=self._report("dws.sql"),
                    relative_path="dws.sql",
                    export_base=Path(tmp),
                )

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                resolve_source_download_path(
                    task={"source_type": "local", "source_ref": tmp},
                    report=self._report("dws.sql"),
                    relative_path="../secret.sql",
                    export_base=Path(tmp),
                )

    def test_task_report_paths_cannot_read_another_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "task-a.sql").write_text("A", encoding="utf-8")
            (root / "task-b.sql").write_text("B", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                resolve_source_download_path(
                    task={"source_type": "local", "source_ref": str(root)},
                    report=self._report("task-a.sql"),
                    relative_path="task-b.sql",
                    export_base=root,
                )

    def test_task_run_returns_task_bound_relative_download_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_file = Path(tmp) / "目录" / "dws.sql"
            source_file.parent.mkdir()
            source_file.write_text("select 1", encoding="utf-8")
            run = audit_engine.TaskRun.__new__(audit_engine.TaskRun)
            run.task_id = 42
            run._source_download_paths = source_relative_paths([source_file], tmp)
            self.assertEqual(
                run.download_url(source_file),
                "/api/audit-tasks/42/source-file?path=%E7%9B%AE%E5%BD%95/dws.sql",
            )

    def test_download_route_returns_json_404_and_attachment(self):
        import app as app_module  # noqa: E402

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_file = root / "dws.sql"
            source_file.write_text("select 1", encoding="utf-8")
            task = {"source_type": "local", "source_ref": str(root), "repo": str(root)}
            report = self._report("dws.sql")
            modules = SimpleNamespace(re_service=SimpleNamespace(get_export_base=lambda: root))
            with patch.object(app_module, "load_audit_task", return_value=task), \
                 patch.object(app_module, "get_task_report_row", return_value={"report_json": json.dumps(report)}), \
                 patch.object(audit_engine, "_mods", modules):
                response = app_module.app.test_client().get("/api/audit-tasks/1/source-file?path=dws.sql")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, b"select 1")
                self.assertIn("attachment", response.headers["Content-Disposition"])
                response.close()
                missing = app_module.app.test_client().get("/api/audit-tasks/1/source-file?path=missing.sql")
                self.assertEqual(missing.status_code, 404)
                self.assertEqual(missing.get_json()["error"], "source file is not part of this audit task")
                missing.close()


if __name__ == "__main__":
    unittest.main()
