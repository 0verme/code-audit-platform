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
