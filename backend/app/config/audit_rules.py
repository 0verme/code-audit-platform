"""Safe, cached loading for non-secret audit business rules.

The configuration is deliberately restricted to structured values.  It never
accepts SQL, connection data, or arbitrary filesystem locations from YAML.
"""
from __future__ import annotations

import copy
import logging
import os
import threading
from pathlib import Path
from typing import Any

import yaml

LOGGER = logging.getLogger(__name__)
_LOCK = threading.Lock()
_CACHE: dict[str, Any] | None = None

DEFAULT_RULES: dict[str, Any] = {
    "display": {
        "highlight_result_source_systems": [],
        "calendar_labels": {},
    },
    "hcyt": {"schedule": {
        "real_job_plan_names": [
            "PLAN_CBS_CBSRUN_REAL_DWS_DAY", "PLAN_DWS_CBS_CBSRUN_DH_XQDATA_REAL",
            "PLAN_REAL_CBS_CBSRUN_LDXJC_HOUR", "PLAN_REAL_CBS_CBSRUN_LDXJC_REAL",
            "PLAN_REAL_DWS_DWD_IJEP_REAL", "PLAN_REAL_KUANYE_KUANYENEW_REAL",
            "PLAN_REAL_TA_LCXSQK_HALF_HOUR",
        ],
        "invalid_plan_names": ["PLAN_PROV_LOCAL_SEND_DAY"],
        "plan_name_rules": [
            {"contains": "DWD", "allowed": ["PLAN_PROV_DWD_LOCAL_DAY", "PLAN_DWS_DWD_DAY"]},
            {"contains": "DWP", "allowed": ["PLAN_PROV_DWP_LOCAL_DAY", "PLAN_DWS_DWP_DAY"]},
            {"contains": "DWM", "allowed": ["PLAN_DWS_DWM_DWS_DWM_DAY", "PLAN_DWS_DWM_MODEL", "PLAN_PROV_DWM_LOCAL_DAY"]},
        ],
        "allowed_domains": ["EDWS_DOMAIN", "CMS_DOMAIN", "NOVA_DOMAIN", "CBSRUN_DOMAIN", "IS_DOMAIN", "EXPORT_DOMAIN"],
        "disabled_status_values": ["9", "9.0"], "enabled_status_values": ["1", "1.0"],
        "realtime_priority_values": ["99", "99.0"],
        "realtime_calendar_plans": ["PLAN_DWS_DWM_MODEL", "PLAN_DWS_DWM_DWS_DWM_DAY"],
        "realtime_calendar_value": "SYS_EVERYDAY_CALENDAR",
        "forbidden_domain_plan_keywords": ["PLAN_SA_RECV", "PLAN_SA_MIDD", "PLAN_DWS_RDS"],
        "forbidden_domain": "EDWS_DOMAIN",
        "sequence_name_rules": [
            {"contains": "DWD", "allowed": ["SEQ_DWS_DWD_DAY", "SEQ_PROV_DWD_LOCAL_DAY", "0.0"]},
            {"contains": "DWP", "allowed": ["SEQ_DWS_DWP_DAY", "SEQ_PROV_DWP_LOCAL_DAY", "0.0"]},
            {"contains": "DWM", "allowed": ["SEQ_DWS_DWM_DWS_DWM_DAY", "SEQ_PROV_DWM_LOCAL_DAY", "SEQ_DWS_DWM_MODEL_LON", "SEQ_DWS_DWM_MODEL_GLA", "SEQ_DWS_DWM_MODEL_COM", "0.0"]},
        ],
        "dependency_required_job_keywords": ["JOB_DWS_DWS_DWF", "JOB_DWS_DWS_DWO", "JOB_PROV_DWS_", "DWUPRR", "DWM", "DWA", "DWP", "SEND", "LOCAL"],
        "dependency_exceptions": ["JOB_SA_RECV"],
        "late_plan_names": ["PLAN_DWS_WLD_DWS_DWF_DAY", "PLAN_DWS_CA_DWS_DWF_DAY", "PLAN_DWS_BICA_DWS_DWF_DAY", "PLAN_JZZF_MBP_NTCP_REAL_DWS_DAY", "PLAN_REAL_CBS_CBSRUN_LDXJC_DAY", "PLAN_DWS_KDW_PAM_DWS_DWF_DAY"],
        "late_plan_exceptions": ["PLAN_JZZF_MBP_NTCP_REAL_DWS_DAY", "PLAN_REAL_CBS_CBSRUN_LDXJC_DAY"],
        "realtime_dependency_exception": "PLAN_JZZF_MBP_NTCP_REAL_DWS_DAY",
        "forbidden_dependency_plans": ["PLAN_JZZF_MBP_NTCP_REAL_DWS_DAY", "PLAN_DWS_KDW_PAM_DWS_DWF_DAY"],
        "required_predecessors": {"JOB_DWS_DWS_DWUPRR_GJYW_ACCT_OPEN_INFO_R_00_DAY": ["JOB_DWS_DWS_DWF_F_AGT_SAVB_BASICINFO_R_ACC_DAY", "JOB_DWS_DWS_DWF_F_AGT_SAVB_ACCTINFO_R_ACC_DAY", "JOB_DWS_DWS_DWF_F_EVT_SAVR_OPENBOOK_R_00_DAY", "JOB_DWS_DWS_DWF_F_PTY_TABLE_R_00_DAY"]},
    }},
}

def _config_path() -> Path:
    override = os.environ.get("AUDIT_RULES_CONFIG")
    if override:
        candidate = Path(override).expanduser()
        if candidate.suffix.lower() not in {".yaml", ".yml"}:
            raise ValueError("AUDIT_RULES_CONFIG must point to a YAML file")
        return candidate
    return Path(__file__).resolve().parents[3] / "configs" / "audit_rules.yaml"

def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if key not in base:
            LOGGER.warning("Ignoring unknown audit rule key: %s", key)
            continue
        if isinstance(base[key], dict):
            if not isinstance(value, dict):
                raise TypeError("audit rule %s must be a mapping" % key)
            if not base[key]:
                if not all(isinstance(item_key, str) and isinstance(item_value, str) for item_key, item_value in value.items()):
                    raise TypeError("audit rule %s must map strings to strings" % key)
                base[key] = value
            else:
                _merge(base[key], value)
        elif isinstance(base[key], list):
            if not isinstance(value, list) or not all(isinstance(item, (str, dict)) for item in value):
                raise TypeError("audit rule %s must be a list of strings or mappings" % key)
            base[key] = value
        elif isinstance(base[key], str):
            if not isinstance(value, str):
                raise TypeError("audit rule %s must be a string" % key)
            base[key] = value
        else:
            base[key] = value
    return base

def load_audit_rules(*, path: Path | None = None) -> dict[str, Any]:
    """Load a rules file safely, falling back to in-code defaults on failure."""
    rules = copy.deepcopy(DEFAULT_RULES)
    try:
        config_path = path or _config_path()
        if not config_path.exists():
            return rules
        with config_path.open("r", encoding="utf-8") as stream:
            supplied = yaml.safe_load(stream) or {}
        if not isinstance(supplied, dict):
            raise TypeError("audit rules root must be a mapping")
        return _merge(rules, supplied)
    except Exception as exc:
        LOGGER.warning("Audit rules configuration ignored; using safe defaults: %s", exc)
        return rules

def get_audit_rules() -> dict[str, Any]:
    global _CACHE
    with _LOCK:
        if _CACHE is None:
            _CACHE = load_audit_rules()
        return copy.deepcopy(_CACHE)

def refresh_audit_rules(*, path: Path | None = None) -> dict[str, Any]:
    """Test-friendly cache refresh; production callers normally use get_audit_rules."""
    global _CACHE
    with _LOCK:
        _CACHE = load_audit_rules(path=path)
        return copy.deepcopy(_CACHE)
