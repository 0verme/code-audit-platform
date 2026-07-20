from __future__ import annotations

import ast
import importlib
from pathlib import Path


AUDIT_PACKAGE = Path(__file__).resolve().parents[2] / "app" / "modules" / "audit"
WORKFLOWS_PACKAGE = AUDIT_PACKAGE / "workflows"
WORKFLOW_NAMES = {"fine_report", "hcyt", "nups"}


def _absolute_import(module_name: str, path: Path, node: ast.ImportFrom) -> str:
    if not node.level:
        return node.module or ""
    relative_name = "." * node.level + (node.module or "")
    package_parts = module_name.split(".")
    package = module_name if path.name == "__init__.py" else ".".join(package_parts[:-1])
    return importlib.util.resolve_name(relative_name, package)


def test_workflows_do_not_import_another_workflow_runner():
    for workflow in WORKFLOW_NAMES:
        workflow_root = WORKFLOWS_PACKAGE / workflow
        for path in workflow_root.rglob("*.py"):
            relative = path.relative_to(AUDIT_PACKAGE.parents[2])
            module_name = ".".join(relative.with_suffix("").parts)
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))

            for node in ast.walk(tree):
                imported_modules: list[str] = []
                if isinstance(node, ast.ImportFrom):
                    imported_modules.append(_absolute_import(module_name, path, node))
                elif isinstance(node, ast.Import):
                    imported_modules.extend(alias.name for alias in node.names)

                for imported_module in imported_modules:
                    for other_workflow in WORKFLOW_NAMES - {workflow}:
                        forbidden = f"app.modules.audit.workflows.{other_workflow}.runner"
                        assert imported_module != forbidden, (
                            f"{path} imports another workflow runner: {forbidden}"
                        )


def test_legacy_runtime_modules_alias_canonical_modules():
    legacy_dispatcher = importlib.import_module("app.modules.audit.workflow_dispatcher")
    canonical_dispatcher = importlib.import_module("app.modules.audit.core.dispatcher")
    legacy_executor = importlib.import_module("app.modules.audit.executor")
    canonical_executor = importlib.import_module("app.modules.audit.core.executor")

    assert legacy_dispatcher is canonical_dispatcher
    assert legacy_executor is canonical_executor
