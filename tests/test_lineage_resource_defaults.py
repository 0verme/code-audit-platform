import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from lineage import mapping_compat
from lineage import paths


def workbook(path, header, row):
    book = Workbook()
    sheet = book.active
    sheet.append(header)
    sheet.append(row)
    book.save(path)
    book.close()


class LineageResourceDefaultTests(unittest.TestCase):
    def test_default_paths_are_module_relative_and_do_not_reference_retired_package(self):
        self.assertEqual(paths.MAPPING_XLSX_PATH, BACKEND_DIR / "data" / "lineage" / "mapping.xlsx")
        self.assertEqual(paths.MAPPING_DB_PATH, BACKEND_DIR / "data" / "lineage" / "mapping_lineage.db")
        self.assertNotIn("svn_check", str(paths.MAPPING_XLSX_PATH))
        self.assertNotIn("svn_check", str(paths.MAPPING_DB_PATH))

    def test_default_resolution_does_not_depend_on_current_working_directory(self):
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary_directory:
            try:
                os.chdir(temporary_directory)
                self.assertEqual(paths.resolve_mapping_xlsx_path(), paths.MAPPING_XLSX_PATH)
                self.assertEqual(paths.resolve_mapping_db_path(), paths.MAPPING_DB_PATH)
            finally:
                os.chdir(original_cwd)

    def test_environment_overrides_support_absolute_relative_and_empty_values(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            absolute_xlsx = Path(temporary_directory) / "override.xlsx"
            absolute_db = Path(temporary_directory) / "override.db"
            with patch.dict(os.environ, {"LINEAGE_MAPPING_EXCEL_PATH": str(absolute_xlsx), "LINEAGE_MAPPING_DB_PATH": str(absolute_db)}):
                self.assertEqual(paths.resolve_mapping_xlsx_path(), absolute_xlsx)
                self.assertEqual(paths.resolve_mapping_db_path(), absolute_db)
            with patch.dict(os.environ, {"LINEAGE_MAPPING_EXCEL_PATH": "", "LINEAGE_MAPPING_DB_PATH": "relative/cache.db"}):
                self.assertEqual(paths.resolve_mapping_xlsx_path(), paths.MAPPING_XLSX_PATH)
                self.assertEqual(paths.resolve_mapping_db_path(), BACKEND_DIR / "relative" / "cache.db")

    def test_real_chinese_headers_and_english_case_insensitive_headers_build_edges(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            chinese_xlsx = Path(temporary_directory) / "chinese.xlsx"
            workbook(
                chinese_xlsx,
                [" 上游表名 ", "上游字段", "\ufeff目标表名", "目标字段"],
                ["ODS.SOURCE_TABLE", "SOURCE_COLUMN", "DM.TARGET_TABLE", "TARGET_COLUMN"],
            )
            self.assertEqual(mapping_compat.load_lineage_edges_from_xlsx(chinese_xlsx)[0]["source_table"], "ODS.SOURCE_TABLE")
            self.assertEqual(mapping_compat.load_lineage_edges_from_xlsx(chinese_xlsx)[0]["target_table"], "DM.TARGET_TABLE")

            english_xlsx = Path(temporary_directory) / "english.xlsx"
            workbook(english_xlsx, [" SOURCE_TABLE ", "SOURCE_COLUMN", "TARGET_TABLE", "TARGET_COLUMN"], ["src", "c1", "tgt", "c2"])
            self.assertEqual(mapping_compat.load_lineage_edges_from_xlsx(english_xlsx)[0]["target_column"], "c2")

    def test_missing_default_resources_are_explicit_unavailable_and_do_not_create_files(self):
        with patch.dict(os.environ, {"LINEAGE_MAPPING_EXCEL_PATH": "", "LINEAGE_MAPPING_DB_PATH": ""}):
            missing_xlsx = paths.resolve_mapping_xlsx_path()
            missing_db = paths.resolve_mapping_db_path()
            with self.assertLogs("lineage.xlsx_loader", level="ERROR") as xlsx_logs:
                with self.assertRaisesRegex(FileNotFoundError, "Lineage mapping Excel does not exist"):
                    mapping_compat.load_lineage_edges_from_xlsx()
            self.assertIn(str(missing_xlsx), "\n".join(xlsx_logs.output))
            self.assertFalse(missing_xlsx.exists())

            with self.assertLogs("lineage.traversal", level="ERROR") as db_logs:
                with self.assertRaisesRegex(FileNotFoundError, "Lineage mapping SQLite cache does not exist"):
                    mapping_compat.find_start_nodes_in_sqlite("demo.source", "column")
            self.assertIn(str(missing_db), "\n".join(db_logs.output))
            self.assertFalse(missing_db.exists())


if __name__ == "__main__":
    unittest.main()
