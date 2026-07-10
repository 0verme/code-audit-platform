# Runtime DB And Metadata DB Boundary

## Scope

This document records the current boundary between runtime DB storage and `svn_check` metadata storage.

This round is documentation-only:

- no file migration
- no business-logic change
- no runtime-store semantic change
- no schema merge
- no table rename
- no profile-default adjustment

## Runtime DB Boundary

Runtime DB is owned by `backend/db`.

Its responsibility is platform runtime persistence, including:

- audit tasks
- task reports
- review details
- runtime execution status

Current runtime schema sources are:

- `backend/db/sql/postgresql/schema.sql`
- `backend/db/sql/dws/schema.sql`
- `backend/db/sql/sqlite/schema.sql`

Current runtime table naming and migration contract is jointly defined by:

- `backend/db/tables.py`
- `backend/db/sql/*/schema.sql`
- `backend/db/sql/postgresql/migrate_runtime_tables.sql`

These files must not be changed independently as if one file were the only source of truth.

## Metadata DB Boundary

Metadata DB initialization for `svn_check` is owned by `backend/svn_check/migrate`.

Current metadata schema source is:

- `backend/svn_check/migrate/postgres_schema.sql`

This SQL file is the metadata-table initialization entry still used by:

- `backend/scripts/init_pg.py`

It is not runtime schema, and it must not be merged with `backend/db/sql/*/schema.sql`.

## Must-Keep Runtime Paths

The following paths are part of the active runtime path and must be retained:

- `backend/db`
- `backend/db/runtime_store.py`
- `backend/db/schema.py`
- `backend/db/tables.py`
- `backend/db/sql/*/schema.sql`

## Compatibility Layer Dependencies

The following paths remain active compatibility-layer dependencies and must be retained:

- `backend/svn_check/shared/db`
- `backend/svn_check/shared/lineage/mapping_sqlite.py`
- `backend/svn_check/migrate/postgres_schema.sql`

Current documented dependents include:

- `backend/svn_check/services/audit_metadata_service.py`
- `backend/svn_check/services/db_service.py`
- `backend/svn_check/shared/lineage/mapping_sqlite.py`
- `backend/scripts/init_pg.py`

## Legacy Archive Candidates

The following path is only documented as an archive candidate:

- `backend/svn_check/shared/graph`

Current wording boundary:

- no confirmed main-flow reference has been identified in the current scan
- this is not equivalent to "confirmed useless"
- do not delete it directly

Future archival requires full reference scanning and test confirmation.

## High-Risk Prohibitions

Do not do the following in a documentation round:

- modify `backend/audit/engine.py` behavior
- modify `runtime_store` read/write semantics
- merge runtime schema and metadata schema
- delete `backend/svn_check/shared/db`
- delete `backend/svn_check/shared/lineage/mapping_sqlite.py`
- delete `backend/svn_check/shared/graph`
- rename database tables or fields
- alter migration SQL semantics
- relax existing tests

## Next-Phase Suggestions

Suggested later-phase work, not implemented here:

- verify runtime and metadata call paths end to end
- audit metadata profile propagation explicitly
- define ownership rules for runtime schema changes across `tables.py`, `schema.sql`, and migration SQL
- shrink `backend/svn_check/shared/db` toward a shim only after full test coverage exists
- split `mapping_sqlite.py` by responsibility only after initialization order, cache behavior, and caller contracts are covered by tests
