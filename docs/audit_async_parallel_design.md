# Async Parallel Audit Design

## Current Execution Flow

The current API already creates an `audit_tasks` row and starts work in a
background thread, but report data is still all-or-nothing. The frontend enters a
task waiting view and polls `/api/audit-tasks/<id>` until the task leaves
`running` or `queued`; only then does it request `/api/audit-tasks/<id>/report`.

Current backend sequence:

1. `POST /api/audit-tasks` validates `sourceRef`, infers `sourceType`, detects
   workflow, inserts an `audit_tasks` row with `status='running'`, then calls
   `engine.start_task(...)`.
2. `engine.start_task` creates a daemon thread and runs `TaskRun.run()`.
3. `TaskRun.run()` loads the copied rule modules from `backend/svn_check`.
4. It reads the source:
   - local source: `workspace_service.load_local_workspace`
   - SVN source: `svn_service.svn_main`
5. It updates progress to analysis and dispatches by workflow:
   - `run_hcyt`
   - `run_nups`
   - `run_fine`
6. The workflow function runs every rule module and assembles one complete report
   object.
7. The complete report is saved to `task_reports.report_json`; category rows are
   written to `audit_results` for the legacy results API.
8. The frontend can render the final report only after the report row exists.

For HCYT, the current serial order inside `run_hcyt` is:

1. Classify exported files with `hcyt.get_hcyt_type`.
2. Run SQL, script, config, unload, DWO, and DWF rules.
3. Parse and validate schedule Excel files.
4. Run Python program checks using schedule/program metadata.
5. Build asset issues and unified asset issues.
6. Build lineage summary from schedule, SQL, metadata, and Python context.
7. Count severities, optionally run AI analysis, then build final sections.

## Required Prerequisites

These tasks must remain in front of module execution because downstream modules
need their output:

1. Create the audit run or task row and return a stable id.
2. Validate source reference and source type.
3. Load runtime configuration and DB profile before rules need metadata.
4. Load real rule modules and fail fast if imports are unavailable.
5. Read local workspace or SVN changed files.
6. Classify files into workflow-specific buckets.
7. Initialize a shared run state and partial report container.

The changed file list and file classification should be published immediately
after they are known, because they are useful even before rule execution
finishes.

## Parallel Candidates

After prerequisites finish, these HCYT modules can run with bounded concurrency
because they primarily consume independent file groups:

1. trunk conflict section assembly from SVN metadata
2. DWS SQL rules
3. Hive SQL rules
4. schema config JSON rules and table rendering
5. sbin/post script rules
6. recv unload config rules
7. DWO and DWF Python script rules
8. DWS asset issue collection that only depends on the DWS script

Concurrency must be bounded. A default worker count of 3 or 4 is sufficient for
local runs and avoids overwhelming SVN, DB, metadata services, Excel parsing, and
file IO.

## Serial Or Dependency-Gated Tasks

These tasks should stay serial or dependency-gated:

1. Source loading and file classification must finish before rule modules start.
2. Schedule Excel checks depend on schedule file discovery and may touch metadata;
   run them as a guarded task rather than blindly parallelizing them with all IO.
3. Python program checks depend on schedule/program metadata, including `job_df`
   and metadata rows where available.
4. Lineage summary depends on schedule, SQL, metadata, and Python context.
5. AI analysis depends on collected rule counts and target files.
6. Final summary, status, legacy `audit_results` writes, and final
   `task_reports` compatibility writes must wait until all modules have either
   succeeded, skipped, or failed in a degraded state.

## Degradable Modules

Single module failure should update that module to `failed` or `skipped`, capture
the error message and duration, and allow the audit run to continue:

1. DWS/Hive/schema/sbin/recv/DWO/DWF static rule modules.
2. Schedule Excel parsing and schedule rules. A malformed Excel file should not
   fail the whole audit.
3. Metadata-backed annotations such as disabled result tables and source systems.
4. Lineage metadata enrichment.
5. Asset issue enrichment and portal links.
6. AI analysis.
7. Download link generation.

Failures in source validation, rule module import, or workspace/SVN loading are
not degradable because no meaningful audit report can be built without them.

## Current API And Frontend Data Flow

Existing API:

1. `GET /api/health`
2. `GET /api/projects`
3. `GET /api/audit-tasks`
4. `GET /api/audit-tasks/<id>`
5. `POST /api/audit-tasks`
6. `GET /api/audit-tasks/<id>/report`
7. `GET /api/audit-results?task_id=<id>`
8. `GET /api/fine-report/items`

Current frontend API mode flow:

1. `HomePage` submits a payload through `reviewService.createAuditTask`.
2. `App.submit` immediately switches to the results route with `taskId`.
3. `useAuditRun` polls `getAuditTask(taskId)`.
4. While the task is running, `App` renders `RunningView`, not the report page.
5. After completion, `useAuditRun` fetches the full report.
6. `ResultsPage`, `NupsResultsPage`, or `FineReportResultsPage` renders from the
   complete report object.
7. The debug drawer reads task logs, but logs are the primary running-state
   detail today.

## Proposed Incremental Architecture

Introduce an `AuditRunState` that sits beside the existing `audit_tasks` and
`task_reports` compatibility path:

1. `AuditTask` describes a module id, label, dependencies, weight, and callable.
2. `AuditTaskStatus` records `queued`, `running`, `success`, `skipped`, or
   `failed`, plus start/end time, duration, error, and result summary.
3. `AuditRunState` owns the run id, top-level status, module statuses, partial
   report sections, logs, counters, and final compatible report.
4. The existing synchronous-style task creation API remains available and keeps
   the same response shape.
5. New async status and partial-result APIs expose the run state for polling.
6. The frontend report page renders partial sections and skeleton module cards
   while the final compatibility report is still being assembled.

This keeps the first implementation local and testable. SSE or WebSocket can be
added later without changing the task model.
