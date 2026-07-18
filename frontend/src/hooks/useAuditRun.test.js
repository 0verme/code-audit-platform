import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  deriveAuditRunPageStatus,
  isCurrentAuditRunResponse,
  mergePartialReport,
  shouldShowAuditRunFailure,
} from "./useAuditRun.js";

const hookSource = readFileSync(new URL("./useAuditRun.js", import.meta.url), "utf8");

const baseReport = {
  task: {
    status: "warn",
    repo: "",
    workflow: "hcyt",
    revision: "-",
    author: "-",
    startedAt: "-",
    duration: "0s",
    changedFiles: 0,
    checks: 0,
    errors: 0,
    warnings: 0,
    conflicts: 0,
  },
  dws: [],
  hive: [],
  config: [],
  sbin: [],
  recv: [],
  python: [],
  changes: [],
  conflicts: [],
};

test("deriveAuditRunPageStatus tracks running and terminal states", () => {
  assert.equal(deriveAuditRunPageStatus({ status: "running", taskStatus: "running" }, null, null), "running");
  assert.equal(deriveAuditRunPageStatus({ status: "success", taskStatus: "pass" }, null, null), "completed");
  assert.equal(deriveAuditRunPageStatus({ status: "failed", taskStatus: "fail" }, null, null), "failed");
  assert.equal(
    deriveAuditRunPageStatus(
      { status: "success", taskStatus: "fail", finalReportReady: true },
      { finalReportReady: true },
      null,
    ),
    "completed",
  );
});

test("shouldShowAuditRunFailure keeps an execution failure out of the empty result page", () => {
  assert.equal(shouldShowAuditRunFailure("failed", null), true);
  assert.equal(shouldShowAuditRunFailure("failed", { task: { status: "fail" } }), false);
  assert.equal(shouldShowAuditRunFailure("completed", null), false);
});

test("mergePartialReport keeps partial sections and real progress metadata", () => {
  const statusPayload = {
    status: "running",
    taskStatus: "running",
    progress: { total: 3, completed: 1, percent: 33, running: ["dws_sql"] },
    tasks: {
      classify_files: { status: "success", task: { label: "文件分类" } },
      dws_sql: { status: "running", task: { label: "DWS SQL" } },
      hive_sql: { status: "queued", task: { label: "Hive SQL" } },
    },
    task: { repo: "svn://example/repo", workflow: "hcyt", revision: "r1", operator_user: "tester" },
  };
  const partialResult = {
    finalReportReady: false,
    partialReport: {
      changes: [{ path: "demo.sql" }],
      dws: [{ level: "err", file: "demo.sql", rule: "r", msg: "bad" }],
    },
  };

  const report = mergePartialReport(baseReport, statusPayload, partialResult);

  assert.equal(report.task.repo, "svn://example/repo");
  assert.equal(report.task.changedFiles, 1);
  assert.equal(report.task.errors, 1);
  assert.deepEqual(report.changes, [{ path: "demo.sql" }]);
  assert.equal(report.__auditRun.currentModule, "DWS SQL");
  assert.equal(report.__auditRun.progress.percent, 33);
});

test("mergePartialReport returns final report without reshaping legacy fields", () => {
  const finalReport = {
    task: { status: "pass", errors: 0, warnings: 0 },
    assetIssues: [{ issueType: "legacy" }],
    lineageSummary: { resultTables: ["A"] },
  };

  const report = mergePartialReport(baseReport, null, { finalReportReady: true, report: finalReport });

  assert.equal(report.task.status, "pass");
  assert.deepEqual(report.assetIssues, [{ issueType: "legacy" }]);
  assert.deepEqual(report.lineageSummary, { resultTables: ["A"] });
  assert.equal(report.__auditRun.finalReportReady, true);
});

test("automatic polling uses only the combined partial-result request", () => {
  const schedulePollSource = hookSource.slice(
    hookSource.indexOf("const schedulePoll"),
    hookSource.indexOf("const startAuditRun"),
  );
  assert.match(schedulePollSource, /loadPartialResult\(targetRunId, expectedSession\)/);
  assert.doesNotMatch(schedulePollSource, /pollAuditRunStatus\(targetRunId\)/);
});

test("responses from an old audit session cannot overwrite the active audit", () => {
  assert.equal(isCurrentAuditRunResponse({
    activeRunId: 202,
    targetRunId: 101,
    payloadRunId: 101,
    activeSession: 8,
    expectedSession: 7,
  }), false);
  assert.equal(isCurrentAuditRunResponse({
    activeRunId: 202,
    targetRunId: 202,
    payloadRunId: 101,
    activeSession: 8,
    expectedSession: 8,
  }), false);
  assert.equal(isCurrentAuditRunResponse({
    activeRunId: 202,
    targetRunId: 202,
    payloadRunId: 202,
    activeSession: 8,
    expectedSession: 8,
  }), true);
});

test("polling carries a session token through requests and rescheduling", () => {
  const schedulePollSource = hookSource.slice(
    hookSource.indexOf("const schedulePoll"),
    hookSource.indexOf("const startAuditRun"),
  );
  assert.match(schedulePollSource, /loadPartialResult\(targetRunId, expectedSession\)/);
  assert.match(schedulePollSource, /schedulePoll\(targetRunId, expectedSession\)/);
  assert.match(schedulePollSource, /sessionRef\.current !== expectedSession/);
});
