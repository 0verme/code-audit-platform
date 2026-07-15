import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.hcyt_program_runner import run_hcyt_programs  # noqa: E402
from app.modules.audit.result_normalizer import dedupe_tables, normalize_table, text_to_rows  # noqa: E402


class FakeReService:
    def load_xls_to_df(self, path):
        return "PROGRAM_DF"

    def merge_job_program(self, merge_job, merge_program):
        return FakeMerged()

    def build_program_lookup(self, merged, prog_path_col, tail_levels=4):
        return {"lookup": True}

    def build_dependency_table_lookup(self, merged):
        return {"dep": True}

    def build_lineage_row_lookup(self, merged, tail_levels=4):
        return {}

    def get_program_lookup_result(self, program_lookup, path, tail_levels=4):
        return ("JOB_A", "SYS_MONTH_END_CALENDAR", ["DM.TABLE_A", "DM.TABLE_C"])

    def get_yilai_table_from_lookup(self, info, dependency_lookup):
        return info

    def safe_remove_prefix(self, path):
        return Path(path).name

    def get_filename(self, path):
        return Path(path).name

    def read_data_from_file(self, path):
        return "select * from dm.table_a"


class FakeProgramDf:
    columns = ["a", "b", "c", "d", "program_path"]


class FakeMerged:
    index = ()


class FakeHcyt:
    def all_job_df(self, job_df, db_job_rows):
        return "MERGED_JOB"

    def all_program_df(self, program_df):
        return FakeProgramDf()

    def rule_dws_py(self, path):
        return ("program error", "", 0, ["DM.TABLE_A", "DM.TABLE_B", "DM.TABLE_C"])

    def get_program_table_name(self, path):
        return "DM.TABLE_A"


class FakePublicData:
    def all_para_table_lists(self):
        return [("DM.TABLE_B",)]

    def all_job(self):
        return []


class FakePythonRule:
    def build_asset_table_review_issues(self, names, source_module, source):
        return [{"rule": "asset-review", "source": source, "tables": list(names)}]


class FakeDdlRule:
    def collect_root_missing_issues(self, text, source_module, source):
        return [{"rule": "root-missing", "source": source}]


class FakeModules:
    def __init__(self):
        self.re_service = FakeReService()
        self.hcyt = FakeHcyt()
        self.public_data = FakePublicData()
        self.hcyt_python_rule = FakePythonRule()
        self.hcyt_ddl_rule = FakeDdlRule()
        self.text_to_rows = text_to_rows
        self.profile_calls = []

    def load_registered_result_tables(self, *, profile):
        self.profile_calls.append(profile)
        return {"DM.TABLE_A"}


class HcytProgramRunnerTests(unittest.TestCase):
    def test_run_hcyt_programs_aggregates_compare_rows_refs_deps_and_assets(self):
        modules = FakeModules()
        py_scripts, py_rows, ref_tables, deps, asset_issues = run_hcyt_programs(
            ["C:/repo/program.py"],
            job_df="JOB_DF",
            program_xls="program.xlsx",
            db_job_rows=[tuple([None, None, "JOB_A"] + [None] * 20 + ["9"])],
            safe=lambda _label, fn, _default: fn(),
            modules=modules,
            download_url=lambda path: f"download://{Path(path).name}",
            load_result_table_annotations=lambda: ({"DM.TABLE_A"}, {"DM.TABLE_A": ["SYS_A"]}),
            annotate_table=lambda name, disabled, sys_name_map: {
                "name": normalize_table(name),
                "disabled": normalize_table(name) in disabled,
                "sysNames": sys_name_map.get(normalize_table(name), []),
                "highlight": False,
            },
            profile_name="target_profile",
            normalize_table=normalize_table,
            dedupe_tables=dedupe_tables,
            cale_map={"SYS_MONTH_END_CALENDAR": "每月末"},
        )

        self.assertEqual(modules.profile_calls, ["target_profile"])
        self.assertEqual(py_rows[0]["file"], "program.py")
        self.assertEqual(py_scripts[0]["job"], "JOB_A")
        self.assertTrue(py_scripts[0]["jobDisabled"])
        self.assertEqual(py_scripts[0]["freq"], "每月末")
        self.assertEqual(
            [row["state"] for row in py_scripts[0]["result"]],
            ["same", "extra"],
        )
        self.assertEqual(
            ref_tables,
            [
                {"name": "DM.TABLE_A", "type": "result"},
                {"name": "DM.TABLE_B", "type": "src"},
                {"name": "DM.TABLE_C", "type": "mid"},
            ],
        )
        self.assertEqual(deps[0]["lane"], "上游 / 调度依赖表")
        self.assertEqual(deps[1]["nodes"], [{"name": "JOB_A", "q": "", "focus": True}])
        self.assertEqual(len(asset_issues), 2)
        self.assertEqual(
            asset_issues[0],
            {"rule": "asset-review", "source": "program.py", "tables": ["DM.TABLE_A"]},
        )

    def test_run_hcyt_programs_degrades_lookup_and_keeps_focus_shape(self):
        modules = FakeModules()

        def safe(label, fn, default):
            if label == "JOB/PROGRAM 调度关联":
                return default
            return fn()

        py_scripts, py_rows, ref_tables, deps, asset_issues = run_hcyt_programs(
            ["C:/repo/program.py"],
            job_df="JOB_DF",
            program_xls="program.xlsx",
            db_job_rows=[],
            safe=safe,
            modules=modules,
            download_url=lambda path: f"download://{Path(path).name}",
            load_result_table_annotations=lambda: (set(), {}),
            annotate_table=lambda name, disabled, sys_name_map: {
                "name": normalize_table(name),
                "disabled": False,
                "sysNames": [],
                "highlight": False,
            },
            profile_name="target_profile",
            normalize_table=normalize_table,
            dedupe_tables=dedupe_tables,
            cale_map={},
        )

        self.assertEqual(py_scripts[0]["job"], "")
        self.assertEqual(py_scripts[0]["result"], [])
        self.assertIn("调度依赖比对不可用", py_scripts[0]["focus"])
        self.assertEqual(deps, [])
        self.assertEqual(len(asset_issues), 2)

    def test_run_hcyt_programs_skips_asset_review_when_output_table_is_unavailable(self):
        modules = FakeModules()
        modules.hcyt.get_program_table_name = lambda _path: ""

        *_results, asset_issues = run_hcyt_programs(
            ["C:/repo/program.py"],
            job_df=None,
            program_xls=None,
            db_job_rows=None,
            safe=lambda _label, fn, _default: fn(),
            modules=modules,
            download_url=lambda path: f"download://{Path(path).name}",
            load_result_table_annotations=lambda: (set(), {}),
            annotate_table=lambda name, disabled, sys_name_map: {},
            profile_name="target_profile",
            normalize_table=normalize_table,
            dedupe_tables=dedupe_tables,
            cale_map={},
        )

        self.assertEqual(asset_issues, [{"rule": "root-missing", "source": "program.py"}])

    def test_run_hcyt_programs_returns_empty_shape_for_empty_input(self):
        modules = FakeModules()
        result = run_hcyt_programs(
            [],
            job_df=None,
            program_xls=None,
            db_job_rows=None,
            safe=lambda _label, fn, _default: fn(),
            modules=modules,
            download_url=lambda path: path,
            load_result_table_annotations=lambda: (set(), {}),
            annotate_table=lambda name, disabled, sys_name_map: {},
            profile_name="target_profile",
            normalize_table=normalize_table,
            dedupe_tables=dedupe_tables,
            cale_map={},
        )

        self.assertEqual(result, ([], [], [], [], []))


if __name__ == "__main__":
    unittest.main()
