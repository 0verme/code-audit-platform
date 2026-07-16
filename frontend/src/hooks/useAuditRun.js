import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { reviewService } from "../services/reviewService.js";
import { createSingleFlight } from "../utils/singleFlight.js";

export const POLL_INTERVAL_MS = 1500;

export function createIdempotencyKey() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

const TERMINAL_RUN_STATUSES = new Set(["success", "failed"]);
const TERMINAL_TASK_STATUSES = new Set(["pass", "warn", "fail"]);

function getErrorMessage(error) {
  return error?.message || String(error || "unknown error");
}

export function deriveAuditRunPageStatus(statusPayload, partialResult, error, starting = false) {
  if (starting) return "starting";
  if (error && !statusPayload && !partialResult) return "failed";

  const runStatus = statusPayload?.status || partialResult?.status;
  const taskStatus = statusPayload?.taskStatus || partialResult?.taskStatus;
  const finalReportReady = Boolean(statusPayload?.finalReportReady || partialResult?.finalReportReady);

  if (runStatus === "failed") return "failed";
  if (finalReportReady || runStatus === "success" || (taskStatus !== "fail" && TERMINAL_TASK_STATUSES.has(taskStatus))) return "completed";
  if (taskStatus === "fail") return "failed";
  if (runStatus === "running" || taskStatus === "running" || taskStatus === "queued") return "running";
  return statusPayload || partialResult ? "running" : "idle";
}

export function shouldShowAuditRunFailure(pageStatus, finalReport) {
  return pageStatus === "failed" && !finalReport;
}

export function mergePartialReport(baseReport, statusPayload, partialResult) {
  const partialReport = partialResult?.partialReport || statusPayload?.partialReport || {};
  const finalReport = partialResult?.report || partialReport.finalReport || null;
  const task = statusPayload?.task || {};
  const tasks = partialResult?.tasks || statusPayload?.tasks || {};
  const progress = partialResult?.progress || statusPayload?.progress || {};
  const logs = partialResult?.logs || statusPayload?.logs || task.logs || [];
  const report = finalReport || {
    ...baseReport,
    ...partialReport,
    task: {
      ...baseReport.task,
      status: partialResult?.status === "failed" || statusPayload?.status === "failed" ? "fail" : baseReport.task.status,
      repo: task.source_ref || task.repo || baseReport.task.repo,
      sourceRef: task.source_ref || task.sourceRef || baseReport.task.sourceRef,
      sourceType: task.source_type || task.sourceType || baseReport.task.sourceType,
      workflow: task.workflow || baseReport.task.workflow,
      revision: task.revision || baseReport.task.revision,
      author: task.operator_user || task.author || baseReport.task.author,
      startedAt: task.started_at || task.startedAt || baseReport.task.startedAt,
      duration: task.duration || baseReport.task.duration,
      changedFiles: partialReport.changes?.length ?? baseReport.task.changedFiles,
      conflicts: partialReport.conflicts?.length ?? baseReport.task.conflicts,
      errors: countIssues(partialReport, "err"),
      warnings: countIssues(partialReport, "warn"),
      checks: Object.keys(tasks).length || baseReport.task.checks,
    },
    logs,
  };

  return {
    ...report,
    __auditRun: {
      pageStatus: deriveAuditRunPageStatus(statusPayload, partialResult, null),
      statusPayload,
      partialResult,
      tasks,
      progress,
      logs,
      currentModule: getCurrentModule(tasks, progress),
      finalReportReady: Boolean(partialResult?.finalReportReady || statusPayload?.finalReportReady),
    },
  };
}

function countIssues(partialReport, level) {
  const sections = ["dws", "hive", "config", "sbin", "recv", "python"];
  return sections.reduce((total, key) => {
    const rows = Array.isArray(partialReport[key]) ? partialReport[key] : [];
    return total + rows.filter((row) => row.level === level).length;
  }, 0);
}

function getCurrentModule(tasks, progress) {
  const runningKey = progress?.running?.[0] || Object.keys(tasks || {}).find((key) => tasks[key]?.status === "running");
  if (!runningKey) return "";
  return tasks[runningKey]?.task?.label || runningKey;
}

export function useAuditRun(runId) {
  const timerRef = useRef(null);
  const stoppedRef = useRef(false);
  const startFlightRef = useRef(null);
  if (!startFlightRef.current) startFlightRef.current = createSingleFlight();
  const [activeRunId, setActiveRunId] = useState(runId || null);
  const [statusPayload, setStatusPayload] = useState(null);
  const [partialResult, setPartialResult] = useState(null);
  const [error, setError] = useState(null);
  const [starting, setStarting] = useState(false);

  const stopPolling = useCallback(() => {
    stoppedRef.current = true;
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const loadPartialResult = useCallback(async (targetRunId = activeRunId) => {
    if (!targetRunId) return null;
    const payload = await reviewService.getAuditRunPartialResult(targetRunId);
    setPartialResult(payload);
    return payload;
  }, [activeRunId]);

  const pollAuditRunStatus = useCallback(async (targetRunId = activeRunId) => {
    if (!targetRunId) return null;
    const payload = await reviewService.getAuditRunStatus(targetRunId);
    setStatusPayload(payload);
    return payload;
  }, [activeRunId]);

  const schedulePoll = useCallback((targetRunId) => {
    if (stoppedRef.current || !targetRunId) return;
    timerRef.current = setTimeout(async () => {
      try {
        const status = await pollAuditRunStatus(targetRunId);
        const partial = await loadPartialResult(targetRunId);
        const terminal = isTerminalAuditRun(status, partial);
        if (terminal) {
          stopPolling();
          return;
        }
        schedulePoll(targetRunId);
      } catch (pollError) {
        setError(new Error(getErrorMessage(pollError)));
        schedulePoll(targetRunId);
      }
    }, POLL_INTERVAL_MS);
  }, [loadPartialResult, pollAuditRunStatus, stopPolling]);

  const startAuditRun = useCallback((payload) => (
    startFlightRef.current.run(async () => {
      stopPolling();
      stoppedRef.current = false;
      setStarting(true);
      setError(null);
      setStatusPayload(null);
      setPartialResult(null);
      try {
        const created = await reviewService.startAuditRun(payload, {
          idempotencyKey: createIdempotencyKey(),
        });
        const nextRunId = created?.runId ?? created?.run_id ?? created?.id;
        setActiveRunId(nextRunId || null);
        setStarting(false);
        if (nextRunId) {
          await pollAuditRunStatus(nextRunId);
          await loadPartialResult(nextRunId);
          schedulePoll(nextRunId);
        }
        return created;
      } catch (startError) {
        setStarting(false);
        setError(new Error(getErrorMessage(startError)));
        throw startError;
      }
    })
  ), [loadPartialResult, pollAuditRunStatus, schedulePoll, stopPolling]);

  useEffect(() => {
    stopPolling();
    stoppedRef.current = false;
    setActiveRunId(runId || null);
    setStatusPayload(null);
    setPartialResult(null);
    setError(null);
    setStarting(false);
    if (!runId) return undefined;

    (async () => {
      try {
        const status = await pollAuditRunStatus(runId);
        const partial = await loadPartialResult(runId);
        if (!isTerminalAuditRun(status, partial)) {
          schedulePoll(runId);
        }
      } catch (pollError) {
        setError(new Error(getErrorMessage(pollError)));
      }
    })();

    return stopPolling;
  }, [loadPartialResult, pollAuditRunStatus, runId, schedulePoll, stopPolling]);

  const pageStatus = deriveAuditRunPageStatus(statusPayload, partialResult, error, starting);
  const running = pageStatus === "starting" || pageStatus === "running";

  return useMemo(() => ({
    runId: activeRunId,
    task: statusPayload?.task || null,
    statusPayload,
    partialResult,
    tasks: partialResult?.tasks || statusPayload?.tasks || {},
    progress: partialResult?.progress || statusPayload?.progress || {},
    logs: partialResult?.logs || statusPayload?.logs || statusPayload?.task?.logs || [],
    report: partialResult?.report || partialResult?.partialReport?.finalReport || null,
    error,
    errorMessage: error ? getErrorMessage(error) : "",
    pageStatus,
    running,
    starting,
    startAuditRun,
    pollAuditRunStatus,
    loadPartialResult,
    stopPolling,
  }), [
    activeRunId,
    error,
    loadPartialResult,
    pageStatus,
    partialResult,
    pollAuditRunStatus,
    running,
    starting,
    startAuditRun,
    statusPayload,
    stopPolling,
  ]);
}

function isTerminalAuditRun(statusPayload, partialResult) {
  return (
    TERMINAL_RUN_STATUSES.has(statusPayload?.status) ||
    TERMINAL_TASK_STATUSES.has(statusPayload?.taskStatus) ||
    partialResult?.finalReportReady
  );
}
