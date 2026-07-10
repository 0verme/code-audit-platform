import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
SVN_CHECK_DIR = BACKEND_DIR / "svn_check"
for path in (BACKEND_DIR, SVN_CHECK_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from audit.checks import dependency as new_dependency  # noqa: E402
from audit.checks import fine_rule as new_fine_rule  # noqa: E402
from audit.checks import nups_rule as new_nups_rule  # noqa: E402
from audit.checks.hcyt import ddl_rule as new_ddl_rule  # noqa: E402
from audit.rules import asset_issue as new_asset_issue  # noqa: E402
from audit.rules import portal_link_builder as new_portal_links  # noqa: E402
from metadata.services import public_data as new_public_data  # noqa: E402

from core import asset_issue as legacy_asset_issue  # noqa: E402
from core import fine_rule as legacy_fine_rule  # noqa: E402
from core import nups_rule as legacy_nups_rule  # noqa: E402
from core import public_data as legacy_public_data  # noqa: E402
from core.hcyt import ddl_rule as legacy_ddl_rule  # noqa: E402
from services import portal_link_builder as legacy_portal_links  # noqa: E402
from shared.graph import dependency as legacy_dependency  # noqa: E402


class AuditNewImportPathTests(unittest.TestCase):
    def test_legacy_rule_modules_resolve_to_new_implementations(self):
        self.assertIs(legacy_asset_issue, new_asset_issue)
        self.assertIs(legacy_portal_links, new_portal_links)
        self.assertIs(legacy_fine_rule, new_fine_rule)
        self.assertIs(legacy_nups_rule, new_nups_rule)
        self.assertIs(legacy_ddl_rule, new_ddl_rule)
        self.assertIs(legacy_public_data, new_public_data)
        self.assertIs(legacy_dependency, new_dependency)


if __name__ == "__main__":
    unittest.main()
