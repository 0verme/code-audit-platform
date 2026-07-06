# Database Profile Migration Plan

## Scope

This inventory covers the platform runtime database tables managed by
`backend/database.py`:

- `projects`
- `audit_tasks`
- `task_reports`
- `audit_results`
- `fine_report_items`

The `backend/svn_check/shared/lineage/mapping_sqlite.py` module also uses
SQLite, but it manages a separate lineage mapping cache and is outside the five
platform runtime tables targeted by this migration.

## Current SQLite Usage Points

`backend/database.py`

- Imports `sqlite3` directly.
- Defines `DB_PATH = backend/data/app.db`.
- `get_connection()` opens `sqlite3.connect(DB_PATH)`.
- Sets `connection.row_factory = sqlite3.Row`.
- `init_db()` creates all five runtime tables with SQLite DDL.
- `_migrate_audit_tasks()` uses `PRAGMA table_info(audit_tasks)` and
  `ALTER TABLE ... ADD COLUMN` to patch old databases.
- Seed data is inserted with SQLite `?` placeholders.

`backend/app.py`

- Imports `get_connection` and `init_db` from `database.py`.
- Calls `init_db()` during Flask app import/startup.
- Uses `connection.execute(... ? ...)` for task, report, result, project, and
  FineReport item reads/writes.
- Uses `cursor.lastrowid` after inserting `audit_tasks`.
- Converts `sqlite3.Row` to `dict` for JSON responses.

`backend/engine.py`

- Imports `get_connection` from `database.py`.
- Updates `audit_tasks.logs_json`, progress, step, status, duration, finished
  timestamp, and error.
- Writes `task_reports` with `INSERT OR REPLACE`.
- Deletes and rewrites `audit_results` rows for a task.
- Uses SQLite `?` placeholders throughout the runtime table writes.

`backend/dev_selfcheck.py`

- Imports `get_connection` and `init_db`.
- Creates self-check `audit_tasks` rows and reads `cursor.lastrowid`.
- This is a development helper, not a frontend API path, but it should keep
  working through the compatibility layer.

## Table Structures

`projects`

| Column | Current SQLite Type | Notes |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Surrogate key |
| `name` | `TEXT NOT NULL` | Display name |
| `project_key` | `TEXT NOT NULL` | Workflow/project key |
| `repo_path` | `TEXT NOT NULL` | Source repository/path |
| `workflow` | `TEXT NOT NULL` | Workflow key |
| `description` | `TEXT NOT NULL` | Description |

`audit_tasks`

| Column | Current SQLite Type | Notes |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Surrogate key |
| `repo` | `TEXT NOT NULL` | Legacy source reference |
| `source_ref` | `TEXT NOT NULL DEFAULT ''` | Normalized source reference |
| `workflow` | `TEXT NOT NULL` | Workflow key |
| `status` | `TEXT NOT NULL` | `queued`/`running`/`pass`/`fail` |
| `revision` | `TEXT NOT NULL` | VCS revision or `-` |
| `author` | `TEXT NOT NULL` | Legacy operator |
| `operator_user` | `TEXT NOT NULL DEFAULT ''` | Normalized operator |
| `client_ip` | `TEXT NOT NULL DEFAULT ''` | Request client IP |
| `started_at` | `TEXT NOT NULL` | Text timestamp |
| `duration` | `TEXT NOT NULL` | Display duration |
| `ai_enabled` | `INTEGER NOT NULL DEFAULT 0` | Boolean flag |
| `debug_enabled` | `INTEGER NOT NULL DEFAULT 0` | Boolean flag |
| `progress` | `INTEGER NOT NULL DEFAULT 0` | Percent |
| `step` | `TEXT NOT NULL DEFAULT ''` | Current step |
| `finished_at` | `TEXT` | Completion timestamp |
| `error` | `TEXT` | Error text |
| `logs_json` | `TEXT NOT NULL DEFAULT '[]'` | JSON array string |
| `source_type` | `TEXT NOT NULL DEFAULT 'svn'` | Source type |

`task_reports`

| Column | Current SQLite Type | Notes |
| --- | --- | --- |
| `task_id` | `INTEGER PRIMARY KEY` | Also references `audit_tasks(id)` |
| `report_json` | `TEXT NOT NULL` | Full report JSON string |
| `created_at` | `TEXT NOT NULL` | Text timestamp |

`audit_results`

| Column | Current SQLite Type | Notes |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Surrogate key |
| `task_id` | `INTEGER NOT NULL` | References `audit_tasks(id)` |
| `category` | `TEXT NOT NULL` | Result category |
| `file_name` | `TEXT NOT NULL` | File path/name |
| `line_no` | `INTEGER NOT NULL` | Line number |
| `rule_name` | `TEXT NOT NULL` | Rule name |
| `level` | `TEXT NOT NULL` | Severity |
| `message` | `TEXT NOT NULL` | Finding text |

`fine_report_items`

| Column | Current SQLite Type | Notes |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Surrogate key |
| `title` | `TEXT NOT NULL` | Report title |
| `file_path` | `TEXT NOT NULL` | Report file path |
| `report_type` | `TEXT NOT NULL` | Report type |
| `change_type` | `TEXT NOT NULL` | Change type |
| `connection_name` | `TEXT NOT NULL` | Data source name |
| `focus` | `TEXT NOT NULL` | Review focus |
| `dataset_sql` | `TEXT NOT NULL` | Dataset SQL text |
| `dataset_rows` | `TEXT NOT NULL` | Row count description |
| `issues_json` | `TEXT NOT NULL` | JSON array string |
| `ref_tables_json` | `TEXT NOT NULL` | JSON array string |

## Current Business Read/Write Entrypoints

Project configuration

- `GET /api/projects` in `backend/app.py`
- Reads `projects` through `get_connection()`.
- Seeded by `init_db()`.

Recent audit list and task detail

- `GET /api/audit-tasks` in `backend/app.py`
- `GET /api/audit-tasks/<task_id>` in `backend/app.py`
- `_fail_orphan_tasks()` in `backend/app.py` updates interrupted task rows.
- `TaskRun.update()` and `TaskRun.finish()` in `backend/engine.py` update task
  logs, progress, status, duration, finish time, and error.

Task creation

- `POST /api/audit-tasks` in `backend/app.py`
- Inserts `audit_tasks`, then uses `cursor.lastrowid`.
- `backend/dev_selfcheck.py` also creates local self-check tasks.

Task report

- `GET /api/audit-tasks/<task_id>/report` reads `task_reports`.
- `TaskRun.finish()` writes `task_reports` and currently depends on
  SQLite-style `INSERT OR REPLACE`.

Audit details

- `GET /api/audit-results` reads `audit_results`.
- `TaskRun.save_category_rows()` deletes task-scoped rows and inserts current
  rows.
- `init_db()` inserts initial demo rows.

FineReport demo/check data

- `GET /api/fine-report/items` reads `fine_report_items`.
- `init_db()` inserts initial demo rows.
- API code deserializes `issues_json` and `ref_tables_json`.

## SQLite to PostgreSQL/DWS Compatibility Risks

- `AUTOINCREMENT` is SQLite-specific. PG/DWS should use identity columns or
  sequences.
- `lastrowid` is SQLite cursor behavior. PG/DWS should use `RETURNING id` or a
  runner-level insert helper.
- `sqlite3.Row` and `row_factory` do not exist in PG/DWS drivers. The DB layer
  should normalize rows to `dict`.
- SQLite `?` placeholders differ from PG/DWS `%s` placeholders. Application SQL
  should use one internal style and let the runner translate.
- `INSERT OR REPLACE` is SQLite-specific and can delete/reinsert rows. Replace
  with a portable upsert abstraction or explicit delete/insert/update sequence.
- SQLite `PRAGMA table_info` migration checks are not portable. Future schema
  initialization should use dialect-specific DDL files and conservative
  `CREATE TABLE IF NOT EXISTS`.
- Timestamp columns are currently text. PG/DWS can use `TIMESTAMP`, but the
  compatibility layer must preserve the API's string output format.
- JSON is stored as text. Keep JSON as `TEXT` across all three engines and keep
  serialization/deserialization in Python.
- Default seed data contains internal-looking demo source references in existing
  code. Do not copy those into docs or config templates.
- DWS compatibility should avoid PostgreSQL-only features such as `jsonb`,
  advanced `ON CONFLICT`, and assumptions about `search_path`.

## Reference Project Patterns to Reuse

The reference project keeps the useful DB access code in
`data-asset-portal/backend/app/db/gaussdb.py` and its config template in
`data-asset-portal/backend/configs/database.example.yaml`.

Reusable ideas:

- A committed `database.example.yaml` and ignored real config files.
- Profile-based configuration with an environment variable override for config
  path and profile name.
- Per-profile DB type normalization.
- SQLite path resolution relative to the backend/project root.
- Connection factories per engine.
- A single SQL execution surface for fetch and execute operations.
- Placeholder normalization from application-level `?` to PG `%s`.
- Conservative docs and `.gitignore` rules that exclude real connection files.
- Tests that exercise SQLite directly and mock external DB drivers instead of
  requiring a real PG/DWS instance by default.

Items not to copy directly:

- The asset portal business table names and services.
- GaussDB JDBC/JAR behavior unless this project later explicitly needs JDBC.
- Real `database.yaml` or local test config files.

## Target Layered Design

`backend/db/profiles.py`

- Load `backend/configs/database.yaml` when present.
- Support `CODE_AUDIT_DB_CONFIG_PATH` override.
- Support `CODE_AUDIT_DB_PROFILE` override.
- Validate `sqlite`, `postgresql`, and `dws` profile types.
- Default to an in-code SQLite profile pointing at `backend/data/app.db`.

`backend/db/connection.py`

- Create DB-API compatible connections for each profile type.
- Use `sqlite3` for SQLite.
- Use an available PostgreSQL driver for PostgreSQL/DWS.
- Do not store real credentials in code.

`backend/db/sql_runner.py`

- Provide `query_one`, `query_all`, `execute`, `execute_many`, and
  `transaction`.
- Normalize rows to dictionaries.
- Normalize placeholders per DB type.
- Provide an insert helper that returns inserted IDs.

`backend/db/schema.py` plus dialect SQL files

- Load and execute the correct DDL for `sqlite`, `postgresql`, or `dws`.
- Use `CREATE TABLE IF NOT EXISTS`.
- Avoid destructive schema operations.

`backend/database.py`

- Remain the compatibility module for existing business code.
- Keep public function names where possible.
- Internally use profiles, connection factories, SQL runner, and schema
  initialization.
- Keep frontend response shapes unchanged.

## Planned Follow-up Rounds

Round 1

- Add `backend/db/profiles.py`.
- Add `backend/configs/database.example.yaml`.
- Update `.gitignore` for real database config files.
- Add unit tests for profile loading and friendly missing-config errors.

Round 2

- Add connection factory, SQL runner, and DB error classes.
- Test SQLite memory/file connections and mock PG/DWS drivers.
- Test placeholder conversion, dict rows, transactions, and insert IDs.

Round 3

- Add schema initialization module and three DDL files for the five runtime
  tables.
- Test SQLite initialization and mock PG/DWS DDL execution.

Round 4

- Refactor `backend/database.py` behind its existing API.
- Preserve current Flask and engine behavior while routing through the new DB
  layer.
- Add compatibility tests for project/task/report/result list workflows.

Round 5

- Replace remaining direct SQLite access in business paths.
- Leave unrelated SQLite cache utilities documented if they are outside the
  five-table runtime database scope.
- Add regression coverage for task details, projects, and FineReport items.

Round 6

- Add `backend/scripts/migrate_sqlite_to_profile.py`.
- Support dry-run, row-count reporting, idempotent copy, and JSON text
  preservation.

Round 7

- Add operator docs for SQLite local development, PG/DWS configuration, schema
  initialization, migration, rollback, and optional integration tests.
- Add skipped-by-default PG/DWS integration test scaffolding.

Round 8

- Run final regression and sensitive-info scans.
- Produce the acceptance report with commits, files, default profile, migration
  steps, and residual manual confirmations.
