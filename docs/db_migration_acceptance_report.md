# Database Migration Acceptance Report

## Commit Map

| Round | Commit | Message |
| --- | --- | --- |
| Round 0 | `2a01486` | `docs: add db profile migration plan` |
| Round 1 | `3b3acb4` | `feat: add database profile config loader` |
| Round 2 | `4646eb2` | `feat: add cross database sql runner` |
| Round 3 | `e8198a9` | `feat: add multi database schema initialization` |
| Round 4 | `b4e8bbc` | `refactor: route database module through db profiles` |
| Round 5 | `7be26d7` | `refactor: remove direct sqlite dependencies` |
| Round 6 | `2e2e61d` | `feat: add sqlite to profile migration script` |
| Round 7 | `2256433` | `docs: add database profile migration guide` |
| Round 8.1 | `c29b9a6` | `chore: sanitize sample internal references` |
| Round 8.2 test fix | `d4645da` | `test: update lineage summary fake module` |
| Round 8.2 report | see final HEAD | `docs: add database migration acceptance report` |

## File Summary

Modified files:

- `.gitignore`
- `backend/app.py`
- `backend/database.py`
- `backend/dev_selfcheck.py`
- `backend/engine.py`
- `backend/svn_check/core/hcyt/schedule_rule.py`
- `backend/svn_check/services/re_service.py`
- `frontend/src/config/auditWorkflows.test.js`
- `frontend/src/mock/data.js`
- `tests/test_engine_lineage_summary.py`
- `tests/test_local_audit_task.py`
- `静态原型代码/data.js`
- `静态原型代码/home.jsx`

New files:

- `backend/configs/database.example.yaml`
- `backend/db/__init__.py`
- `backend/db/connection.py`
- `backend/db/errors.py`
- `backend/db/profiles.py`
- `backend/db/schema.py`
- `backend/db/schema_dws.sql`
- `backend/db/schema_pg.sql`
- `backend/db/schema_sqlite.sql`
- `backend/db/sql_runner.py`
- `backend/scripts/migrate_sqlite_to_profile.py`
- `docs/db_migration.md`
- `docs/db_migration_acceptance_report.md`
- `docs/db_profile_migration_plan.md`
- `docs/db_profiles.md`
- `tests/integration/test_db_profiles_integration.py`
- `tests/test_database_compat.py`
- `tests/test_db_profiles.py`
- `tests/test_db_schema.py`
- `tests/test_migrate_sqlite_to_profile.py`
- `tests/test_sql_runner.py`

Deleted files: none in the committed migration chain.

## Current Default Profile

Default database profile: `sqlite`

Default SQLite database path:

```text
backend/data/app.db
```

Verified with:

```bash
D:\miniconda3\python.exe -c "import sys; sys.path.insert(0, 'backend'); from db.profiles import get_active_profile; p=get_active_profile(); print(p.name, p.type, p.config.get('path') or p.config.get('database'))"
```

Result:

```text
sqlite sqlite E:\AI生成代码\code-audit-platform\backend\data\app.db
```

## Availability

SQLite remains available by default. No environment variables are required.

PostgreSQL enablement:

1. Copy `backend/configs/database.example.yaml` to ignored `backend/configs/database.yaml`.
2. Fill a `postgresql` profile with test or environment values.
3. Set `CODE_AUDIT_DB_CONFIG_PATH=backend\configs\database.yaml`.
4. Set `CODE_AUDIT_DB_PROFILE=local_pg`.
5. Start the backend; schema initialization runs automatically.

DWS enablement:

1. Configure a `dws` profile in the ignored local config.
2. Set `CODE_AUDIT_DB_CONFIG_PATH=backend\configs\database.yaml`.
3. Set `CODE_AUDIT_DB_PROFILE=local_dws`.
4. Start the backend; schema initialization runs automatically.

SQLite data migration:

```bash
D:\miniconda3\python.exe backend\scripts\migrate_sqlite_to_profile.py --source backend\data\app.db --target-profile local_pg --dry-run
D:\miniconda3\python.exe backend\scripts\migrate_sqlite_to_profile.py --source backend\data\app.db --target-profile local_pg
D:\miniconda3\python.exe backend\scripts\migrate_sqlite_to_profile.py --source backend\data\app.db --target-profile local_dws --dry-run
```

The migration script covers `projects`, `audit_tasks`, `task_reports`,
`audit_results`, and `fine_report_items`. It skips existing primary keys and
does not delete, truncate, or overwrite target data.

## Test Evidence

Passed:

```bash
D:\miniconda3\python.exe -m unittest discover -s tests
```

Result: 79 backend tests passed.

Passed:

```bash
npm test
```

Result: 21 frontend config tests passed.

Passed with expected skip:

```bash
D:\miniconda3\python.exe -m unittest tests.integration.test_db_profiles_integration
```

Result: 1 integration test skipped by default. It requires
`CODE_AUDIT_RUN_DB_INTEGRATION=1` and a profile whose database name contains
`test`.

Runtime note: Python emitted a `RequestsDependencyWarning` from the local
Miniconda environment and one `ResourceWarning` during full backend discovery.
The test suite completed successfully.

## Scan Evidence

Commands run:

```bash
git grep -n -E "password|passwd|token|secret|jdbc|postgres://|postgresql://|dws.*://|([0-9]{1,3}\.){3}[0-9]{1,3}" -- .
git grep -n -E "sqlite3\.connect|backend/data/app\.db|lastrowid|row_factory|INSERT OR REPLACE|datetime\('now'\)" -- .
```

Sensitive scan classification:

- Placeholder config values remain in committed examples: `127.0.0.1`,
  `change_me`, `demo_password`, and `db.example.com`.
- Security documentation contains words such as `password`, `token`, `secret`,
  and `jdbc` as policy/checklist text.
- Tests intentionally retain fake sensitive strings such as `password=secret`,
  `token=abc`, `jdbc:postgresql://192.0.2.10/demo`, and `192.0.2.10` to verify
  sanitization and redaction behavior. `192.0.2.10` is an RFC 5737
  documentation address, not a private/internal address.
- `frontend/src/mock/data.js` contains masked demo values such as
  `password=***`, `token=***`, and `jdbc:demo://***`.
- No real account, password, token, real private IP, or real database
  connection string was identified in the committed migration changes.

SQLite residual classification:

- `backend/db/connection.py`, `backend/db/sql_runner.py`, and `backend/database.py`
  contain SQLite compatibility-layer code by design.
- `backend/db/schema_sqlite.sql` contains SQLite DDL by design.
- `backend/scripts/migrate_sqlite_to_profile.py` reads the source SQLite file by
  design.
- `backend/svn_check/shared/lineage/mapping_sqlite.py` is a separate lineage
  cache utility outside the five platform runtime tables.
- Round 0 inventory documentation still describes the old SQLite state for
  traceability.

## Remaining Worktree State

Current uncommitted items are pre-existing or generated and were not included in
the migration commits:

- `.codex/`
- `backend/backend.err.log`
- `backend/backend.log`
- `frontend/frontend.err.log`
- `frontend/frontend.log`
- `hcyt/local-hcyt-workspace/dws.sql` deleted
- `hcyt/local-hcyt-workspace/hive.sql` deleted
- `hcyt/local-hcyt-workspace/sql/` untracked
- `hcyt/local-hcyt-workspace/调度/` untracked

Manual confirmation still needed: decide whether to keep, ignore, clean, or
commit the unrelated `hcyt/local-hcyt-workspace` generated workspace changes
and runtime logs.
