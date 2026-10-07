import ast
import importlib.util
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
REGISTRY_PATH = BACKEND_DIR / "app" / "modules" / "audit" / "rules" / "registry.py"
REGISTRY_SPEC = importlib.util.spec_from_file_location("audit_rule_registry", REGISTRY_PATH)
assert REGISTRY_SPEC is not None and REGISTRY_SPEC.loader is not None
REGISTRY_MODULE = importlib.util.module_from_spec(REGISTRY_SPEC)
sys.modules[REGISTRY_SPEC.name] = REGISTRY_MODULE
REGISTRY_SPEC.loader.exec_module(REGISTRY_MODULE)
RULES = REGISTRY_MODULE.RULES
RULES_BY_ID = REGISTRY_MODULE.RULES_BY_ID
resolve_rule = REGISTRY_MODULE.resolve_rule
rule_inventory = REGISTRY_MODULE.rule_inventory


AUDIT_ROOT = BACKEND_DIR / "app" / "modules" / "audit"
NON_BUSINESS_FINDING_IDS = frozenset(
    {
        # File-presence INFO rows describe workflow/display status, not business rules.
        "hcyt.sql.file_present",
        "hcyt.hive.file_present",
        # This only announces a changed config file; it does not validate its contents.
        "hcyt.config.production_source",
        # These findings report unavailable metadata or checker execution failures.
        "hcyt.schedule.job.asset_metadata_unavailable",
        "hcyt.sql.asset_metadata_unavailable",
        "fine.menu.execution_error",
        "fine.authority.execution_error",
        "fine.report.execution_error",
        # The source loop is unreachable because sstb_name is initialized to [].
        "fine.report.forbidden_table",
    }
)


def _call_name(node):
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _literal_string(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _business_finding_ids(config):
    ids = set()
    trees = {}
    for path in AUDIT_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        trees[path] = tree
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node)
            if name in {"Finding", "add"} and node.args:
                value = _literal_string(node.args[0])
                if value:
                    ids.add(value)
            if name == "create_audit_asset_issue":
                for keyword in node.keywords:
                    if keyword.arg == "issue_type":
                        value = _literal_string(keyword.value)
                        if value:
                            ids.add(value)

    # schedule_rule builds stable IDs from configured DWD/DWP/DWM keys.
    schedule = config["hcyt"]["schedule"]
    ids.update(
        f"hcyt.schedule.plan.{keyword.lower()}_name"
        for keyword in schedule["plan_name_rules"]
    )
    ids.update(
        f"hcyt.schedule.job.{keyword.lower()}_sequence"
        for keyword in schedule["sequence_name_rules"]
    )

    # sensitive_sql combines each explicit suffix with the two workflow namespaces.
    sensitive_path = AUDIT_ROOT / "workflows" / "hcyt" / "checks" / "sensitive_sql.py"
    sensitive_tree = trees[sensitive_path]
    suffixes = set()
    for node in ast.walk(sensitive_tree):
        if not isinstance(node, ast.Call) or _call_name(node) != "_finding":
            continue
        suffix = next(
            (_literal_string(keyword.value) for keyword in node.keywords if keyword.arg == "suffix"),
            None,
        )
        if suffix:
            suffixes.add(suffix)

    namespaces = set()
    for tree in trees.values():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _call_name(node) != "scan_sensitive_sql":
                continue
            namespace = next(
                (_literal_string(keyword.value) for keyword in node.keywords if keyword.arg == "namespace"),
                None,
            )
            if namespace:
                namespaces.add(namespace)
    ids.update(f"{namespace}.{suffix}" for namespace in namespaces for suffix in suffixes)
    return ids - NON_BUSINESS_FINDING_IDS


def _source_rule_severities(config):
    severities = defaultdict(set)
    trees = [
        ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for path in AUDIT_ROOT.rglob("*.py")
    ]
    for tree in trees:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node)
            if name in {"Finding", "add"} and node.args:
                rule_id = _literal_string(node.args[0])
                level = _literal_string(node.args[2]) if len(node.args) > 2 else None
                if rule_id and level:
                    severities[rule_id].add(level)
            if name == "create_audit_asset_issue":
                rule_id = next(
                    (_literal_string(keyword.value) for keyword in node.keywords if keyword.arg == "issue_type"),
                    None,
                )
                level = next(
                    (_literal_string(keyword.value) for keyword in node.keywords if keyword.arg == "severity"),
                    None,
                )
                if rule_id and level:
                    severities[rule_id].add("warn" if level == "warning" else level)

    schedule = config["hcyt"]["schedule"]
    for tree in trees:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _call_name(node) == "add" and node.args and isinstance(node.args[0], ast.JoinedStr):
                expression = ast.unparse(node.args[0])
                level = _literal_string(node.args[2]) if len(node.args) > 2 else None
                if level and "hcyt.schedule.plan." in expression:
                    for keyword in schedule["plan_name_rules"]:
                        severities[f"hcyt.schedule.plan.{keyword.lower()}_name"].add(level)
                if level and "hcyt.schedule.job." in expression and "sequence" in expression:
                    for keyword in schedule["sequence_name_rules"]:
                        severities[f"hcyt.schedule.job.{keyword.lower()}_sequence"].add(level)
            if _call_name(node) == "_finding":
                suffix = next(
                    (_literal_string(keyword.value) for keyword in node.keywords if keyword.arg == "suffix"),
                    None,
                )
                level = next(
                    (_literal_string(keyword.value) for keyword in node.keywords if keyword.arg == "level"),
                    None,
                )
                if suffix and level:
                    for namespace in ("hcyt.sql", "hcyt.hive"):
                        severities[f"{namespace}.{suffix}"].add(level)
    return {rule_id: levels for rule_id, levels in severities.items() if rule_id not in NON_BUSINESS_FINDING_IDS}


def _resolve_config_path(config, dotted_path):
    value = config
    for component in dotted_path.split("."):
        assert isinstance(value, dict), f"{dotted_path}: {component} is not under a mapping"
        assert component in value, f"Unknown audit config path: {dotted_path}"
        value = value[component]
    return value


def test_registry_ids_are_unique_and_match_business_finding_ids():
    assert len(RULES_BY_ID) == len(RULES)
    assert Counter(rule.workflow for rule in RULES) == {
        "hcyt": 115,
        "nups": 39,
        "fine-report": 26,
    }
    assert len(RULES) == 180
    config_path = BACKEND_DIR / "configs" / "audit_rules.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    discovered = _business_finding_ids(config)
    assert set(RULES_BY_ID) == discovered
    assert all(resolve_rule(rule_id) is RULES_BY_ID[rule_id] for rule_id in discovered)


def test_registry_severity_matches_existing_execution_behavior():
    config_path = BACKEND_DIR / "configs" / "audit_rules.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    actual = _source_rule_severities(config)
    assert set(actual) == set(RULES_BY_ID)
    conditional = {rule_id: levels for rule_id, levels in actual.items() if len(levels) > 1}
    assert conditional == {"fine.report.sensitive_fields": {"err", "warn"}}
    for rule in RULES:
        levels = actual[rule.id]
        if len(levels) == 1:
            assert rule.default_severity in levels, rule.id
        else:
            assert rule.default_severity in levels, rule.id


def test_registry_required_metadata_and_contract_values_are_valid():
    allowed_workflows = {"hcyt", "nups", "fine-report"}
    allowed_categories = {
        "sql", "ddl", "python", "script", "schedule", "dependency",
        "metadata", "asset_registry", "config", "menu", "permission", "report",
    }
    allowed_severities = {"err", "warn", "info"}
    required_text_fields = (
        "id", "title", "description", "rationale", "trigger_condition", "artifact",
    )

    for rule in RULES:
        for field in required_text_fields:
            assert getattr(rule, field).strip(), f"{rule.id}: missing {field}"
        assert rule.workflow in allowed_workflows, rule.id
        assert rule.category in allowed_categories, rule.id
        assert rule.default_severity in allowed_severities, rule.id
        assert "检查" not in rule.title, rule.id
        assert isinstance(rule.config_keys, tuple), rule.id
        assert rule.implementation, rule.id
        for config_key in rule.config_keys:
            assert config_key.strip(), f"{rule.id}: empty config key"


def test_implementation_module_and_function_are_locatable():
    for rule in RULES:
        for implementation in rule.implementation:
            assert implementation.module.startswith("app."), rule.id
            relative = Path(*implementation.module.split("."))
            module_path = BACKEND_DIR / relative.with_suffix(".py")
            assert module_path.is_file(), f"{rule.id}: missing {module_path}"
            tree = ast.parse(module_path.read_text(encoding="utf-8-sig"), filename=str(module_path))
            functions = {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            assert implementation.function in functions, (
                f"{rule.id}: missing {implementation.module}.{implementation.function}"
            )


def test_config_keys_resolve_in_the_policy_configuration():
    config_path = BACKEND_DIR / "configs" / "audit_rules.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    module_sources = {}
    for rule in RULES:
        for implementation in rule.implementation:
            path = BACKEND_DIR / Path(*implementation.module.split(".")).with_suffix(".py")
            module_sources[implementation.module] = path.read_text(encoding="utf-8-sig")
        for config_key in rule.config_keys:
            _resolve_config_path(config, config_key)
            leaf = config_key.split(".")[-1]
            if leaf in {"DWD", "DWP", "DWM"}:
                leaf = config_key.split(".")[-2]
            consumer = "\n".join(module_sources[item.module] for item in rule.implementation)
            assert leaf in consumer, f"{rule.id}: config path not consumed by its implementation: {config_key}"


def test_machine_inventory_exposes_the_required_projection():
    required = {"id", "workflow", "category", "title", "severity", "artifact", "implementation", "config_keys"}
    inventory = rule_inventory()
    assert len(inventory) == len(RULES)
    assert all(required <= set(entry) for entry in inventory)


def test_golden_samples_have_catalog_ready_rule_text():
    expected = {
        "hcyt.schedule.job.push_job_missing": "asset_registry",
        "nups.ddl.column_comment": "ddl",
        "fine.report.sensitive_fields": "report",
    }
    for rule_id, category in expected.items():
        rule = resolve_rule(rule_id)
        assert rule is not None
        assert rule.category == category
        assert rule.title and "检查" not in rule.title
        assert rule.description and rule.rationale and rule.trigger_condition
        assert rule.artifact and rule.implementation
