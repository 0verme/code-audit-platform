# Database Migration Guide

## Runtime Default

The backend no longer uses SQLite when no explicit platform database config is
provided. With no `AUDIT_DATABASE_CONFIG` or `CODE_AUDIT_DB_PROFILE`, the
app reuses the metadata database config from:

```text
backend/database.yaml
```

That file must set `backend: postgres`. The runtime platform tables and rule
metadata tables will be created/read in the same PostgreSQL database.

## Move to PostgreSQL or DWS

1. Create `backend/database.yaml` from the template.
2. Add a `postgresql` or `dws` profile with test or environment-specific values.
3. Set `AUDIT_DATABASE_CONFIG` to an absolute path when using a non-default file.
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

## Use SQLite Explicitly For Local Tests

Create a local config with an explicit SQLite profile, then set the profile
environment variables:

```bash
set AUDIT_DATABASE_CONFIG=C:\absolute\path\to\database.yaml
set CODE_AUDIT_DB_PROFILE=sqlite
```

SQLite is no longer a no-config fallback.

## Tests

Default tests use SQLite and mocks:

```bash
D:\miniconda3\python.exe -m unittest tests.test_db_profiles tests.test_sql_runner tests.test_db_schema tests.test_database_compat tests.test_migrate_sqlite_to_profile
```

PG/DWS integration tests are skipped unless
`CODE_AUDIT_RUN_DB_INTEGRATION=1` is set. They must target a database whose name
contains `test`.
