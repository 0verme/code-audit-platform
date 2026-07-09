# `backend/svn_check/shared/db`

## Current Responsibility

This directory is the compatibility adapter layer between old `svn_check` database access and the newer shared DB/profile routing model.

It currently provides:

- DB backend routing
- profile-based query dispatch
- compatibility entry points still imported by legacy-style services

## Active Callers

This directory is still used by:

- `backend/svn_check/services/audit_metadata_service.py`
- `backend/svn_check/services/db_service.py`
- `backend/svn_check/shared/lineage/mapping_sqlite.py`

## Why It Stays

This layer cannot be removed in the short term because active metadata and lineage flows still depend on it.

Deleting it would require logic migration, not just directory cleanup.

## Boundary

- this is not the runtime DB persistence layer
- runtime DB persistence lives under `backend/db`
- this directory primarily supports metadata-side compatibility access
