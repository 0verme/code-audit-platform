import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.hcyt_program_runner import run_hcyt_programs  # noqa: E402
from app.modules.audit.findings import CheckResult  # noqa: E402
from app.modules.audit.result_normalizer import dedupe_tables, normalize_table  # noqa: E402


class FakeProgramDf:
    columns = ["a", "b", "c", "d", "program_path"]


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
        return ("JOB_A", "FREQ", ["DM.TABLE_A", "DM.TABLE_X"])

    def get_yilai_table_from_lookup(self, info, dependency_lookup):
        return info

    def safe_remove_prefix(self, path):
        return Path(path).name

    def get_filename(self, path):
        return Path(path).name

    def read_data_from_file(self, path):
        return ""


class FakeMerged:
    index = ()


class FakeHcyt:
    def all_job_df(self, job_df, db_job_rows):
        return "MERGED_JOB"

    def all_program_df(self, program_df):
        return FakeProgramDf()

    def rule_dws_py(self, path, **_kwargs):
        return CheckResult(artifacts={"sql_tables": ["DM.TABLE_A", "DM.TABLE_B"]})

    def get_program_table_name(self, path):
        return "DM.TABLE_A"


class FakePublicData:
    def all_para_table_lists(self):
        return [("DM.TABLE_B",)]

    def all_job(self):
        return [tuple([None, None, "JOB_A"] + [None] * 20 + ["9"])]


class FakeModules:
    def __init__(self):
        self.re_service = FakeReService()
        self.hcyt = FakeHcyt()
        self.public_data = FakePublicData()
        self.hcyt_python_rule = type(
            "FakePythonRule",
            (),
            {"build_asset_table_review_issues": staticmethod(lambda *args, **kwargs: [])},
        )()
        self.hcyt_ddl_rule = type(
            "FakeDdlRule",
            (),
            {"collect_root_missing_issues": staticmethod(lambda *args, **kwargs: [])},
        )()
        self.profile_calls = []

    def load_registered_result_tables(self, *, profile):
        self.profile_calls.append(profile)
        return {"DM.TABLE_A"}


class HcytProgramRunnerContractTests(unittest.TestCase):
    def test_compare_rows_job_disabled_refs_deps_and_profile_are_stable(self):
        modules = FakeModules()
        py_scripts, _py_rows, ref_tables, deps, asset_issues = run_hcyt_programs(
            ["C:/repo/program.py"],
            job_df="JOB_DF",
            program_xls="program.xlsx",
            db_job_rows=None,
            safe=lambda _label, fn, _default: fn(),
            modules=modules,
            download_url=lambda path: f"download://{Path(path).name}",
            load_result_table_annotations=lambda: ({"DM.TABLE_A"}, {"DM.TABLE_A": ["SYS_A"]}),
            annotate_table=lambda name, disabled, sys_name_map: {
                "name": normalize_table(name),
                "disabled": normalize_table(name) in disabled,
                "sysNames": sys_name_map.get(normalize_table(name), []),
                "highlight": normalize_table(name) in disabled,
            },
            profile_name="profile_a",
            normalize_table=normalize_table,
            dedupe_tables=dedupe_tables,
            cale_map={"FREQ": "每日"},
        )

        self.assertEqual(modules.profile_calls, ["profile_a"])
        self.assertEqual(
            py_scripts[0]["result"],
            [
                {
                    "sql": "DM.TABLE_A",
                    "dep": "DM.TABLE_A",
                    "state": "same",
                    "name": "DM.TABLE_A",
                    "disabled": True,
                    "sysNames": ["SYS_A"],
                    "highlight": True,
                },
                {
                    "sql": None,
                    "dep": "DM.TABLE_X",
                    "state": "extra",
                    "name": "DM.TABLE_X",
                    "disabled": False,
                    "sysNames": [],
                    "highlight": False,
                },
            ],
        )
        self.assertTrue(py_scripts[0]["jobDisabled"])
        self.assertEqual(py_scripts[0]["freq"], "每日")
        self.assertEqual(ref_tables, [{"name": "DM.TABLE_A", "type": "result"}, {"name": "DM.TABLE_B", "type": "src"}])
        self.assertEqual(
            deps,
            [
                {"lane": "上游 / 调度依赖表", "nodes": [{"name": "DM.TABLE_A", "q": ""}, {"name": "DM.TABLE_X", "q": ""}]},
                {"lane": "本次作业", "nodes": [{"name": "JOB_A", "q": "", "focus": True}]},
            ],
        )
        self.assertEqual(asset_issues, [])


if __name__ == "__main__":
    unittest.main()
