# `backend/svn_check/migrate`

## Current Responsibility

This directory stores metadata schema initialization assets for `svn_check`.

Primary file:

- `backend/svn_check/migrate/postgres_schema.sql`

## Boundary

`postgres_schema.sql` is used to initialize metadata tables consumed by legacy-compatible metadata services.

It is not the runtime schema for the audit platform.

Do not confuse it with:

- `backend/db/sql/postgresql/schema.sql`
- `backend/db/sql/dws/schema.sql`
- `backend/db/sql/sqlite/schema.sql`

## Current Main Entry

- `backend/scripts/init_pg.py` reads this SQL file and initializes metadata-side tables in the active PostgreSQL or DWS profile

## High-Risk Notes

- this SQL file and `backend/db/sql/*/schema.sql` cannot be merged directly
- the two schema families serve different domains and different call paths
