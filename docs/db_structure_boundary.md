# DB / Schema / Metadata / Legacy Boundary

## Scope

This document defines the current directory responsibilities and non-negotiable boundaries for the audit platform database layer.

The current implementation intentionally keeps `runtime DB` and `metadata DB` separate:

- `runtime DB`: stores audit platform runtime data such as audit tasks, reports, rule results, and execution records.
- `metadata DB`: stores external metadata consumed by audit rules, such as term roots, schedule metadata, result-table registration, recv mappings, and lineage-related reference data.

These two domains are related at runtime, but they are not the same schema and must not be merged casually.

## Directory Responsibilities

### `backend/db`

This is the current runtime DB main entry for the audit platform.

It owns:

- runtime connection/profile resolution
- runtime table naming and token rendering
- runtime schema loading and initialization
- runtime store read/write operations used by the platform

Primary files:

- `backend/db/schema.py`: runtime schema loader and initializer
- `backend/db/tables.py`: logical-to-physical runtime table mapping
- `backend/db/runtime_store.py`: runtime task/report/result persistence
- `backend/db/sql/postgresql/schema.sql`
- `backend/db/sql/dws/schema.sql`
- `backend/db/sql/sqlite/schema.sql`

### `backend/db/sql/*`

These SQL files are the runtime table structure sources.

Authoritative runtime schema inputs currently live in:

- `backend/db/sql/postgresql/schema.sql`
- `backend/db/sql/dws/schema.sql`
- `backend/db/sql/sqlite/schema.sql`

They define the platform runtime tables for task execution and report persistence. They are not the same thing as `svn_check` metadata schema initialization SQL.

### `backend/svn_check/migrate`

This directory contains metadata-side schema initialization assets for `svn_check`.

Current boundary:

- `backend/svn_check/migrate/postgres_schema.sql` initializes `svn_check` metadata tables.
- It is not the runtime schema for the audit platform.

This file supports metadata queries used by legacy-compatible audit services and lineage-related lookups.

### `backend/svn_check/shared/db`

This is the compatibility adapter layer between old `svn_check` database access and the new shared DB/profile system.

It is still used by:

- `backend/svn_check/services/audit_metadata_service.py`
- `backend/svn_check/services/db_service.py`
- `backend/svn_check/shared/lineage/mapping_sqlite.py`

Short-term conclusion: this layer cannot be deleted yet.

### `backend/svn_check/shared/lineage`

This directory holds lineage-related compatibility logic.

Current focus file:

- `backend/svn_check/shared/lineage/mapping_sqlite.py`

Its current responsibilities are mixed:

- online metadata query
- SQLite cache build
- Excel import
- lineage traversal

Short-term conclusion: only document the mixed responsibility for now; do not split it in this phase.

## Runtime DB vs Metadata DB

### Runtime DB

Purpose:

- persist audit tasks
- persist reports
- persist rule results
- persist runtime execution state

Current main path:

- `backend/audit/engine.py` orchestrates audit execution
- `backend/db/runtime_store.py` persists runtime data
- `backend/db/schema.py` loads runtime schema from `backend/db/sql/*/schema.sql`

### Metadata DB

Purpose:

- provide rule-dependent external metadata
- provide term roots
- provide schedule and job/program metadata
- provide result table registration
- provide recv mapping metadata
- provide lineage-related reference data

Current main path:

- `backend/svn_check/services/audit_metadata_service.py`
- `backend/svn_check/services/db_service.py`
- `backend/svn_check/shared/db/router.py`
- `backend/svn_check/shared/lineage/mapping_sqlite.py`

## Current Main Flow Entries

Runtime DB main entry:

- `backend/db` is the audit platform runtime DB main entry.

Runtime schema entry:

- `backend/db/schema.py` resolves profile-specific runtime schema SQL.

Runtime schema sources:

- `backend/db/sql/postgresql/schema.sql`
- `backend/db/sql/dws/schema.sql`
- `backend/db/sql/sqlite/schema.sql`

Metadata schema init entry:

- `backend/scripts/init_pg.py` loads `backend/svn_check/migrate/postgres_schema.sql`

Legacy-compatible metadata access:

- `backend/svn_check/services/audit_metadata_service.py`
- `backend/svn_check/services/db_service.py`
- `backend/svn_check/shared/db/router.py`

Lineage compatibility entry:

- `backend/svn_check/shared/lineage/mapping_sqlite.py`

## Compatibility Layer Notes

`backend/svn_check/shared/db` is not dead code. It is the current compatibility bridge that allows the copied `svn_check` service stack to keep working while runtime DB access has already been centralized under `backend/db`.

Why it stays for now:

- legacy `svn_check` service code still calls this layer
- metadata queries still depend on it
- lineage helpers still import it directly
- removing it now would force logic migration, not just documentation cleanup

## Why These Directories Must Not Be Moved Yet

- `backend/db` is already the runtime execution path and schema entry used by the platform.
- `backend/svn_check/migrate/postgres_schema.sql` still has a distinct responsibility as metadata schema initialization SQL.
- `backend/svn_check/shared/db` still serves active compatibility imports.
- `backend/svn_check/shared/lineage/mapping_sqlite.py` still bundles multiple operational responsibilities in one module.
- runtime schema expression is still duplicated across Python table definitions, schema SQL, and migration SQL, so moving directories now would increase ambiguity instead of reducing it.

## Known Risks

### `mapping_sqlite.load_registered_result_tables()` default profile risk

`backend/svn_check/shared/lineage/mapping_sqlite.py` defines:

- `load_registered_result_tables(profile: str = 'czcb')`

Current risk:

- `backend/audit/engine.py` calls this function without explicitly passing `profile`
- the implicit default is currently `czcb`
- this needs separate validation and governance in a later phase

This round only records the risk. It does not change behavior.

### Runtime schema has multiple expressions

Runtime table definitions are currently expressed in multiple places:

- `backend/db/tables.py`
- `backend/db/sql/*/schema.sql`
- runtime migration SQL such as `backend/db/sql/postgresql/migrate_runtime_tables.sql`

Current risk:

- schema intent is not yet governed by a single source of truth

This needs later consolidation, but not in this phase.

### Metadata schema SQL and runtime schema SQL cannot be merged directly

The following are not interchangeable and must not be merged directly:

- `backend/svn_check/migrate/postgres_schema.sql`
- `backend/db/sql/*/schema.sql`

Reason:

- they serve different domains
- they back different call paths
- they evolve under different compatibility constraints

## Phased Governance Route

### Phase 0

- document boundaries
- label active compatibility layers
- state non-removal constraints
- record high-risk areas without changing behavior

### Phase 1

- verify runtime vs metadata DB call paths end-to-end
- explicitly audit profile propagation for metadata queries
- validate `mapping_sqlite.load_registered_result_tables()` caller assumptions

### Phase 2

- define a single source of truth strategy for runtime table definitions
- clarify whether migration SQL derives from schema SQL or vice versa
- add ownership rules for runtime schema changes

### Phase 3

- shrink compatibility surface in `backend/svn_check/shared/db`
- separate lineage online query, SQLite cache build, Excel import, and traversal responsibilities when tests and ownership are ready

### Phase 4

- evaluate selective retirement of legacy adapters only after call sites are migrated and verified

## High-Risk Prohibitions

Do not do the following without a dedicated migration round:

- do not treat `backend/svn_check/migrate/postgres_schema.sql` as runtime schema
- do not merge metadata schema SQL into `backend/db/sql/*/schema.sql`
- do not delete `backend/svn_check/shared/db`
- do not split `backend/svn_check/shared/lineage/mapping_sqlite.py` in a docs-only round
- do not assume `tables.py` alone is the runtime schema source of truth
- do not change profile defaults or metadata DB routing as part of documentation cleanup
