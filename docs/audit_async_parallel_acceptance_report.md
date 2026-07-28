# Async Parallel Audit Acceptance Report

> Historical acceptance record. The isolated executor prototype described here
> was never the production execution owner and has since been removed. The
> supported runtime model is currently one process/one worker with workflow-local
> concurrency only.

## Scope

This report covers phases 4-7 of the async audit and progressive report page rollout.

Completed commits:

- `4c0e79f feat: show progressive audit report`
- `573a37e fix: preserve audit result compatibility`
- `63233c9 perf: improve audit execution observability`

## Final Concurrency Model

The product keeps the original synchronous audit API and adds an async run API:

- `POST /api/audit-tasks` remains available for compatibility.
- `POST /api/audit-runs` creates the same underlying task and returns `run_id`.
- `GET /api/audit-runs/<run_id>/status` returns run status, task status, module states, progress, timings, and logs.
- `GET /api/audit-runs/<run_id>/partial-result` returns partial report sections during execution and the final report after completion.

The frontend enters the report page immediately after run creation and polls status plus partial results every 1.5 seconds. Polling stops after a terminal run state or when `finalReportReady` is true.

## Task Ordering

Serial prerequisite tasks:

- Create run and database task row.
- Validate source type and source path.
- Load configuration and workflow.
- Read SVN source or local workspace.
- Classify changed files.
- Initialize the report container and module task states.

Parallel-capable module tasks:

- trunk conflict check.
- DWS SQL check.
- Hive SQL check.
- Configuration file check.
- Post script check.
- Receive/unload configuration check.
- Python static checks where dependencies allow.

Serial tasks and reasons:

- Source reading: downstream modules need the exported file list.
- File classification: module routing depends on classified paths.
- Schedule table check: Python dependency analysis needs schedule artifacts.
- Dependency lineage analysis: depends on schedule and Python outputs.
- Final summary: must merge all module results into the legacy report shape.

## Progressive Report Behavior

The report page now renders before final completion. While running, it shows:

- Run state: starting, running, completed, or failed.
- Current module from real backend task state.
- Completed module count over total modules.
- Error, warning, conflict, failed, and skipped counts.
- Real progress from terminal task count and weighted progress.
- Per-module cards for queued, running, success, skipped, and failed states.
- Per-module duration and a mild "耗时较长" hint over 10 seconds.
- Collapsed execution logs at the bottom.

Completed runs show the final legacy report sections and keep module duration cards visible for troubleshooting.

## Failure Degradation

Single-module failure does not blank the page. Failed modules expose status and error detail in the module board, while completed modules and partial sections remain visible. Final reports preserve compatibility fields including:

- `assetIssues`
- `unifiedAssetIssues`
- `lineageSummary`
- Existing result sections such as `changes`, `dws`, `hive`, `config`, `sbin`, `recv`, `schedule`, `pyScripts`, `refTables`, and `deps`

Audit result status `fail` with `finalReportReady=true` is treated as a completed audit result, not a crashed task.

## Progress Calculation

Progress is based on real task state:

- Backend reports terminal task count and weighted progress.
- Failed and skipped module counts are included in progress metadata.
- Running modules are displayed as running but are not counted as complete.
- The progress bar is not artificially advanced by the frontend.

## Observability

Each module task serializes:

- `startedAt`
- `finishedAt`
- `durationMs`
- `status`
- `error` and `errorMessage`

Run-level serialization includes:

- `startedAt`
- `finishedAt`
- `durationMs`
- `status`
- `error` and `errorMessage`
- `progress.failed`
- `progress.skipped`

## Sample Audit

Local sample workspace:

- `hcyt/local-hcyt-workspace`
- 9 files

Observed run on July 8, 2026:

- Create API returned HTTP 201 in 3.1 seconds.
- First observed partial status: `running/running`, `finalReportReady=false`, elapsed 16.1 seconds.
- Progress observations: 0%, 17%, 70%, 94%, then 100%.
- Final report ready at 87.7 seconds.
- Final status: `fail` as an audit result, with a valid final report.
- Final counts: 9 changed files, 9 checks, 11 errors, 3 warnings, 0 conflicts, 1 asset issue, 1 lineage table.

Performance and experience comparison:

- Before the progressive report page, the user stayed on the waiting experience until the final report was available, about 88 seconds for this sample.
- After the change, the frontend can enter the report page immediately after run creation and progressively fill sections from real backend status and partial-result payloads.

## Verification Commands

Backend:

```powershell
D:\miniconda3\python.exe -m unittest discover tests
```

Result: passed, 97 tests in 206.325 seconds.

Frontend:

```powershell
npm test
npm run build
```

Result: `npm test` passed 26 tests. `npm run build` completed successfully.

Diff and sensitive scan:

```powershell
git diff --check
git diff --cached -- . ':!hcyt/local-hcyt-workspace' | Select-String -Pattern '(?i)(password|passwd|pwd|token|secret|credential|jdbc|odbc|dsn|connectionString|api[_-]?key|access[_-]?key|\b(?:\d{1,3}\.){3}\d{1,3}\b)'
```

Result: no whitespace errors. Staged sensitive scan found no secrets or real internal endpoints. One earlier phase 4 scan matched only the existing localhost default `127.0.0.1:5088`.

## Remaining Risks

- The sample audit still depends on degraded database metadata queries when local database objects are unavailable.
- Some console output comes from reused rule modules and is not yet fully normalized into structured logs.
- The direct `tests.test_local_audit_task` module run can exceed a short timeout, while the full backend suite passes reliably with a longer timeout.

## Rollback

Rollback can be done by reverting the phase commits in reverse order:

```powershell
git revert 63233c9
git revert 573a37e
git revert 4c0e79f
```

The old synchronous endpoint `POST /api/audit-tasks` was retained, so consumers can also switch back to the existing synchronous task flow without deleting the async endpoints.

## Uncommitted Files

At the time this report was written, the only intended uncommitted file is this document before its phase 7 commit.

No `hcyt/local-hcyt-workspace`, log files, database files, startup scripts, or generated build artifacts are intended to be committed.

## Sensitive Information

No real internal IP, account, password, token, or real connection string was added in phases 4-7. The only IP literal seen in staged scans was the existing localhost API default.
