# `backend/svn_check/shared/lineage`

## Current Responsibility

This directory contains lineage-related compatibility logic used by the current audit flow.

Primary file:

- `backend/svn_check/shared/lineage/mapping_sqlite.py`

## Mixed Responsibilities in `mapping_sqlite.py`

The module currently mixes several responsibilities:

- online metadata query
- SQLite cache build
- Excel import
- lineage traversal

## Current Boundary

This mixed design is known and documented.

Short term:

- keep the module in place
- do not split it during docs-only rounds
- use documentation to make the boundary explicit

## Known Risk

`load_registered_result_tables()` defaults to `profile='czcb'`, while current engine-side calls do not explicitly pass `profile`.

This needs later validation and governance, but this round does not change behavior.
