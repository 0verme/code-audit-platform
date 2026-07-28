from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HcytInputFiles:
    path_map: dict
    dws_url: str | None
    hive_url: str | None
    schame_config_lists: list
    sbin_lists: list
    recv_lists: list
    dwo_lists: list
    dwf_lists: list
    dlo_meta_lists: list
    dlo_lists: list
    py_lists: list
    plan_xls: str | None
    seq_xls: str | None
    job_xls: str | None
    program_xls: str | None
    cale_xls: str | None
    grouped: dict
    changes: list
    conflicts: list

    def as_run_inputs(self):
        return (
            self.dws_url, self.hive_url, self.schame_config_lists, self.sbin_lists, self.recv_lists,
            self.dwo_lists, self.dwf_lists, self.py_lists, self.plan_xls, self.seq_xls, self.job_xls,
            self.program_xls, self.cale_xls, self.grouped, self.changes, self.conflicts,
        )


def collect_hcyt_input_files(*, svn_result, re_service, hcyt, build_changes, build_conflicts):
    exported = svn_result["exported_paths"]
    path_map = {re_service.safe_remove_prefix(p): p for p in exported}
    (
        dws_url,
        hive_url,
        schame_config_lists,
        sbin_lists,
        recv_lists,
        dwo_lists,
        dwf_lists,
        dlo_meta_lists,
        dlo_lists,
        py_lists,
        plan_xls,
        seq_xls,
        job_xls,
        program_xls,
        cale_xls,
    ) = hcyt.get_hcyt_type(exported)
    return HcytInputFiles(
        path_map=path_map,
        dws_url=dws_url,
        hive_url=hive_url,
        schame_config_lists=schame_config_lists,
        sbin_lists=sbin_lists,
        recv_lists=recv_lists,
        dwo_lists=dwo_lists,
        dwf_lists=dwf_lists,
        dlo_meta_lists=dlo_meta_lists,
        dlo_lists=dlo_lists,
        py_lists=py_lists,
        plan_xls=plan_xls,
        seq_xls=seq_xls,
        job_xls=job_xls,
        program_xls=program_xls,
        cale_xls=cale_xls,
        grouped={"dws": [], "hive": [], "python": [], "sbin": [], "config": [], "recv": []},
        changes=build_changes(svn_result, path_map),
        conflicts=build_conflicts(svn_result),
    )
