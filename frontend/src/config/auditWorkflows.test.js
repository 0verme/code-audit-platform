import test from "node:test";
import assert from "node:assert/strict";
import {
  buildAuditSubmitPayload,
  canSubmitAudit,
  detectWorkflow,
} from "./auditWorkflows.js";

test("hcyt repository path is detected as HCYT", () => {
  assert.equal(detectWorkflow("svn://10.18.32.7/datawh/branches/202602/hcyt"), "hcyt");
  assert.equal(detectWorkflow("svn://example.com/repos/branches/demo-hcyt"), "hcyt");
});

test("fine-report repository path is detected as FineReport", () => {
  assert.equal(detectWorkflow("https://git.intra/report/fine-report.git"), "fine-report");
});

test("nups repository path is detected as NUPS", () => {
  assert.equal(detectWorkflow("svn://10.18.32.7/pay/nups/trunk"), "nups");
});

test("unmatched repository path returns null", () => {
  assert.equal(detectWorkflow("svn://example.com/repos/branches/unknown-module"), null);
});

test("unmatched repository path cannot be submitted", () => {
  assert.equal(canSubmitAudit("svn://example.com/repos/branches/unknown-module"), false);
  assert.equal(buildAuditSubmitPayload({ path: "svn://example.com/repos/branches/unknown-module" }), null);
});

test("recognized repository path submit payload contains workflow and type", () => {
  assert.deepEqual(
    buildAuditSubmitPayload({
      path: "https://git.intra/report/fine-report.git",
      sourceType: "svn",
      ai: true,
      dbg: true,
    }),
    {
      path: "https://git.intra/report/fine-report.git",
      sourceType: "svn",
      ai: true,
      dbg: true,
      workflow: "fine-report",
      type: "fine-report",
    },
  );
});
