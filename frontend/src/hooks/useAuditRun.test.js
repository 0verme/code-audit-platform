import assert from "node:assert/strict";
import test from "node:test";
import { deriveAuditRunPageStatus, mergePartialReport } from "./useAuditRun.js";

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
