# svn_check Retirement Final Report

Stage 8 retires the `backend/svn_check` compatibility package. The maintained implementations are now under `backend/metadata`, `backend/lineage`, `backend/audit/rules`, `backend/audit/checks`, and `backend/db/metadata/compat`.

References to `svn_check` that remain in the repository are historical migration records, compatibility log names, or external URL values. They are not Python import dependencies or runtime package paths.

The metadata schema remains at `backend/metadata/init/postgres_schema.sql`; runtime schema files remain under `backend/db/sql`. These responsibilities are intentionally separate.
