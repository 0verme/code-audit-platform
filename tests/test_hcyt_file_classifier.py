import unittest
from pathlib import PureWindowsPath

from app.modules.audit.hcyt_file_classifier import collect_hcyt_input_files


class FakeReService:
    def safe_remove_prefix(self, path):
        return PureWindowsPath(path).name


class FakeHcyt:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def get_hcyt_type(self, exported):
        self.calls.append(list(exported))
        return self.result


def hcyt_type_result(**overrides):
    values = {
        "dws_url": None,
        "hive_url": None,
        "schame_config_lists": [],
        "sbin_lists": [],
        "recv_lists": [],
        "dwo_lists": [],
        "dwf_lists": [],
        "_dlo_meta": None,
        "_dlo": None,
        "py_lists": [],
        "plan_xls": None,
        "seq_xls": None,
        "job_xls": None,
        "program_xls": None,
        "cale_xls": None,
    }
    values.update(overrides)
    return tuple(values.values())


class HcytFileClassifierTests(unittest.TestCase):
    def _collect(self, exported, hcyt_result):
        svn_result = {
            "exported_paths": exported,
            "branch_changed_files": ["dws.sql"],
            "trunk_conflict_files": ["hive.sql"],
        }
        hcyt = FakeHcyt(hcyt_result)
        calls = []

        result = collect_hcyt_input_files(
            svn_result=svn_result,
            re_service=FakeReService(),
            hcyt=hcyt,
            build_changes=lambda payload, path_map: calls.append(("changes", payload, path_map)) or [{"file": "dws.sql"}],
            build_conflicts=lambda payload: calls.append(("conflicts", payload)) or [{"file": "hive.sql"}],
        )
        return result, hcyt, calls

    def test_existing_hcyt_classification_slots_are_preserved(self):
        result, hcyt, calls = self._collect(
            [
                r"C:\workspace\dws.sql",
                r"C:\workspace\hive.sql",
                r"C:\workspace\schema_config.json",
                r"C:\workspace\sbin\post.sh",
                r"C:\workspace\recv.json",
                r"C:\workspace\program.py",
                r"C:\workspace\plan.xlsx",
            ],
            hcyt_type_result(
                dws_url=r"C:\workspace\dws.sql",
                hive_url=r"C:\workspace\hive.sql",
                schame_config_lists=[r"C:\workspace\schema_config.json"],
                sbin_lists=[r"C:\workspace\sbin\post.sh"],
                recv_lists=[r"C:\workspace\recv.json"],
                dwo_lists=[r"C:\workspace\dwo.py"],
                dwf_lists=[r"C:\workspace\dwf.py"],
                py_lists=[r"C:\workspace\program.py"],
                plan_xls=r"C:\workspace\plan.xlsx",
                seq_xls=r"C:\workspace\seq.xlsx",
                job_xls=r"C:\workspace\job.xlsx",
                program_xls=r"C:\workspace\program.xlsx",
                cale_xls=r"C:\workspace\cale.xlsx",
            ),
        )

        self.assertEqual(hcyt.calls[0][0], r"C:\workspace\dws.sql")
        self.assertEqual(result.dws_url, r"C:\workspace\dws.sql")
        self.assertEqual(result.hive_url, r"C:\workspace\hive.sql")
        self.assertEqual(result.schame_config_lists, [r"C:\workspace\schema_config.json"])
        self.assertEqual(result.sbin_lists, [r"C:\workspace\sbin\post.sh"])
        self.assertEqual(result.recv_lists, [r"C:\workspace\recv.json"])
        self.assertEqual(result.dwo_lists, [r"C:\workspace\dwo.py"])
        self.assertEqual(result.dwf_lists, [r"C:\workspace\dwf.py"])
        self.assertEqual(result.py_lists, [r"C:\workspace\program.py"])
        self.assertEqual(result.plan_xls, r"C:\workspace\plan.xlsx")
        self.assertEqual(result.seq_xls, r"C:\workspace\seq.xlsx")
        self.assertEqual(result.job_xls, r"C:\workspace\job.xlsx")
        self.assertEqual(result.program_xls, r"C:\workspace\program.xlsx")
        self.assertEqual(result.cale_xls, r"C:\workspace\cale.xlsx")
        self.assertEqual(result.grouped, {"dws": [], "hive": [], "python": [], "sbin": [], "config": [], "recv": []})
        self.assertEqual(result.changes, [{"file": "dws.sql"}])
        self.assertEqual(result.conflicts, [{"file": "hive.sql"}])
        self.assertEqual(calls[0][0], "changes")
        self.assertEqual(calls[1][0], "conflicts")

    def test_path_map_preserves_current_safe_remove_prefix_behavior(self):
        result, _hcyt, calls = self._collect(
            [r"C:\workspace\A\dws.sql", r"C:\workspace\B\dws.sql", r"C:\workspace\program.py"],
            hcyt_type_result(),
        )

        self.assertEqual(result.path_map, {"dws.sql": r"C:\workspace\B\dws.sql", "program.py": r"C:\workspace\program.py"})
        self.assertEqual(calls[0][2], result.path_map)

    def test_empty_file_list_uses_empty_grouped_and_source_payloads(self):
        result, hcyt, _calls = self._collect([], hcyt_type_result())

        self.assertEqual(hcyt.calls, [[]])
        self.assertEqual(result.path_map, {})
        self.assertEqual(result.grouped["python"], [])
        self.assertEqual(result.changes, [{"file": "dws.sql"}])
        self.assertEqual(result.conflicts, [{"file": "hive.sql"}])

    def test_unknown_paths_are_left_to_existing_hcyt_classifier(self):
        result, hcyt, _calls = self._collect(
            [r"C:\workspace\unknown.ext", r"C:\workspace\mixed\SCRIPT.PY"],
            hcyt_type_result(py_lists=[r"C:\workspace\mixed\SCRIPT.PY"]),
        )

        self.assertEqual(hcyt.calls, [[r"C:\workspace\unknown.ext", r"C:\workspace\mixed\SCRIPT.PY"]])
        self.assertEqual(result.py_lists, [r"C:\workspace\mixed\SCRIPT.PY"])


if __name__ == "__main__":
    unittest.main()
