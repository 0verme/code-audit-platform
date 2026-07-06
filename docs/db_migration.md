# Database Migration Guide

## Keep SQLite

Do nothing if you want local SQLite development. With no
`CODE_AUDIT_DB_CONFIG_PATH` or `CODE_AUDIT_DB_PROFILE`, the app uses the default
SQLite profile and creates:

```text
backend/data/app.db
```

## Move to PostgreSQL or DWS

1. Create an ignored local config from the template.
2. Add a `postgresql` or `dws` profile with test or environment-specific values.
3. Set `CODE_AUDIT_DB_CONFIG_PATH`.
4. Set `CODE_AUDIT_DB_PROFILE`.
5. Start the backend; table initialization runs automatically.

All committed examples use placeholders only.

## Migrate Existing SQLite Data

Dry-run first:

```bash
D:\miniconda3\python.exe backend\scripts\migrate_sqlite_to_profile.py --source backend\data\app.db --target-profile local_pg --dry-run
```

Apply after reviewing row counts:

```bash
D:\miniconda3\python.exe backend\scripts\migrate_sqlite_to_profile.py --source backend\data\app.db --target-profile local_pg
```

DWS uses the same script with a DWS profile:

```bash
D:\miniconda3\python.exe backend\scripts\migrate_sqlite_to_profile.py --source backend\data\app.db --target-profile local_dws --dry-run
```

The script migrates only:

- `projects`
- `audit_tasks`
- `task_reports`
- `audit_results`
- `fine_report_items`

It does not delete target data, does not truncate tables, and skips rows whose
primary key already exists.

## Roll Back to SQLite

Unset the profile environment variables:

```bash
set CODE_AUDIT_DB_CONFIG_PATH=
set CODE_AUDIT_DB_PROFILE=
```

Then restart the backend. The app will use `backend/data/app.db` again.

## Tests

Default tests use SQLite and mocks:

```bash
D:\miniconda3\python.exe -m unittest tests.test_db_profiles tests.test_sql_runner tests.test_db_schema tests.test_database_compat tests.test_migrate_sqlite_to_profile
```

PG/DWS integration tests are skipped unless
`CODE_AUDIT_RUN_DB_INTEGRATION=1` is set. They must target a database whose name
contains `test`.
