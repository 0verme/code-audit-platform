# `backend/db`

## Current Responsibility

`backend/db` is the current runtime DB main entry for the audit platform.

This directory owns runtime-side concerns only:

- runtime DB connection/profile access
- runtime schema loading
- runtime table token rendering
- runtime task/report/result persistence

## Runtime Schema Source

The current runtime table structure comes from:

- `backend/db/sql/postgresql/schema.sql`
- `backend/db/sql/dws/schema.sql`
- `backend/db/sql/sqlite/schema.sql`

These files are the runtime schema sources for platform execution storage.

## Main Runtime Flow

- `backend/audit/engine.py` runs audit tasks
- `backend/db/runtime_store.py` writes runtime records
- `backend/db/schema.py` initializes runtime schema from `backend/db/sql/*`

## Boundary With Metadata DB

This directory does not define the `svn_check` metadata schema.

In particular:

- `backend/svn_check/migrate/postgres_schema.sql` is metadata schema initialization SQL
- it is not a replacement for the runtime schema files under `backend/db/sql/*`

## Current Risks

- runtime table definitions are currently expressed in `tables.py`, runtime schema SQL, and migration SQL
- this is not yet a single source of truth
- documentation in this round does not change runtime behavior
