# Database Profiles

## Default Runtime Database

The platform runtime database and rule metadata database use the same config
file:

```text
backend/svn_check/configs/database.yaml
```

That config must use `backend: postgres`. The platform maps its `postgres` block
into the runtime `postgres` profile, so audit runtime tables and rule metadata
tables live in the same PostgreSQL database.

## Config File

Copy the committed template before editing local credentials:

```bash
copy backend\svn_check\configs\database.example.yaml backend\svn_check\configs\database.yaml
```

`backend/svn_check/configs/database.yaml` is ignored by git. Do not commit real
hostnames, usernames, passwords, tokens, or connection strings.

Override the config file path with:

```bash
set CODE_AUDIT_DB_CONFIG_PATH=backend\svn_check\configs\database.yaml
```

Override the active profile with:

```bash
set CODE_AUDIT_DB_PROFILE=local_pg
```

## PostgreSQL Profile

Use placeholder values in committed examples and put real test-only values in
your ignored local config:

```yaml
default_profile: local_pg

profiles:
  local_pg:
    type: postgresql
    host: 127.0.0.1
    port: 5432
    database: code_audit_test
    username: change_me
    password: change_me
    schema: public
```

SQLite is still available only as an explicit test/development profile. Do not
use it as the backend default.

The database name for integration tests must clearly contain `test`.

## DWS Profile

DWS uses the same profile shape and DB-API runner path:

```yaml
profiles:
  local_dws:
    type: dws
    host: 127.0.0.1
    port: 8000
    database: code_audit_test
    username: change_me
    password: change_me
    schema: public
```

Keep DWS SQL in the PG/DWS common subset. The runtime schema avoids `jsonb`,
advanced `ON CONFLICT`, and destructive table operations.

## Schema Initialization

The app initializes the five runtime tables on startup through
`backend/db/schema.py`. To initialize manually from Python:

```bash
D:\miniconda3\python.exe -c "from db.schema import initialize_schema; initialize_schema()"
```

Run that command from the `backend` directory or make sure `backend` is on
`PYTHONPATH`.

## Optional Integration Tests

Integration tests are skipped by default. Enable them only against disposable
test databases:

```bash
set CODE_AUDIT_RUN_DB_INTEGRATION=1
set CODE_AUDIT_DB_CONFIG_PATH=backend\svn_check\configs\database.yaml
set CODE_AUDIT_INTEGRATION_PROFILE=local_pg
D:\miniconda3\python.exe -m unittest tests.integration.test_db_profiles_integration
```

For DWS, set `CODE_AUDIT_INTEGRATION_PROFILE=local_dws`.

The test refuses to run unless the selected profile database name contains
`test`.
