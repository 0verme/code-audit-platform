# `backend/svn_check/shared/graph`

## Current Status

This directory is a historical helper-module candidate.

Current documentation status:

- it is a candidate for historical auxiliary modules that currently have no confirmed main-flow references
- it must not be described as "confirmed unused"
- it must not be deleted directly in the current phase

## Current Boundary

This directory is not part of the documented runtime DB entry under `backend/db`.

It is also not the metadata schema initialization entry under `backend/svn_check/migrate`.

## Handling Rule For This Phase

Treat this directory as an archive candidate only.

Before any future archival or cleanup:

- perform a full reference scan
- verify behavior with test coverage
- confirm there is no hidden operational dependency

This round only records the boundary and does not change any import path or runtime behavior.

## Stage 2 Scan Record

Reference-scan commands used in this round:

- `rg "shared\.graph" backend tests docs`
- `rg "backend/svn_check/shared/graph" backend tests docs`
- `rg "dependency" backend tests docs`
- `rg "build.*graph|cycle|dependency" backend/svn_check backend/audit tests docs`

Scan conclusion for this round:

- no active main-flow import or call site was found for `shared.graph`
- current hits are limited to this directory, planning docs, and string-level mentions of dependency concepts elsewhere
- `dependency.py` currently exposes pure in-memory helpers only and does not touch DB, files, or environment variables

Future re-check requirements before any archival decision:

- rerun the same `rg` scan commands after feature work that touches schedule, lineage, or dependency logic
- keep algorithm-level contract tests passing before changing import paths
- repeat call-chain inspection if any new import reaches `shared.graph` or `dependency.py`

Rollback rule if an external reference is found later:

- stop archival or cleanup work immediately
- restore this directory to active-support status at the current path
- document the new caller, call chain, and operational risk before making further changes
