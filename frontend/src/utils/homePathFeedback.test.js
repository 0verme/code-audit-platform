import assert from "node:assert/strict";
import test from "node:test";
import { detectAuditSource } from "../config/auditSources.js";
import { applyBackendWorkflowDefinitions, detectAuditWorkflow } from "../config/auditWorkflows.js";
import { getHomePathFeedbackState } from "./homePathFeedback.js";

applyBackendWorkflowDefinitions([
  { id: "hcyt", path_keywords: ["/hcyt", "hcyt", "湖仓"] },
  { id: "fine-report", path_keywords: ["/fine-report", "fine_report", "finereport", "report", "报表"] },
  { id: "nups", path_keywords: ["/nups", "统一报送", "pay/nups", "nups"] },
]);

function feedback(path, hasValidated = false, submitError = "") {
  return getHomePathFeedbackState({
    path,
    detectedSource: detectAuditSource(path),
    detectedWorkflow: detectAuditWorkflow(path),
    hasValidated,
    submitError,
  });
}

test("empty paths keep all path feedback hidden", () => {
  assert.deepEqual(feedback(""), {
    hasMatch: false,
    showInputDetection: false,
    showRouteCard: false,
    showSourceError: false,
    showWorkflowError: false,
    showSubmitError: false,
  });
});

test("unvalidated invalid paths do not show red feedback", () => {
  const result = feedback("not a repository");

  assert.equal(result.showInputDetection, false);
  assert.equal(result.showSourceError, false);
  assert.equal(result.showWorkflowError, false);
  assert.equal(result.showRouteCard, false);
});

test("validated invalid paths show only the source error", () => {
  const result = feedback("not a repository", true);

  assert.equal(result.showInputDetection, true);
  assert.equal(result.showSourceError, true);
  assert.equal(result.showWorkflowError, false);
  assert.equal(result.showRouteCard, false);
});

test("matched paths show one workflow card without validation errors", () => {
  const result = feedback("svn://svn.example.com/repository/hcyt");

  assert.equal(result.hasMatch, true);
  assert.equal(result.showInputDetection, true);
  assert.equal(result.showRouteCard, true);
  assert.equal(result.showSourceError, false);
  assert.equal(result.showWorkflowError, false);
});

test("validated feedback clears after correcting a path", () => {
  const invalid = feedback("not a repository", true);
  const corrected = feedback("svn://svn.example.com/repository/fine-report", true);

  assert.equal(invalid.showSourceError, true);
  assert.equal(corrected.showSourceError, false);
  assert.equal(corrected.showWorkflowError, false);
  assert.equal(corrected.showRouteCard, true);
});

test("submit errors remain visible after submit validation", () => {
  assert.equal(feedback("", true, "提交失败").showSubmitError, true);
});

test("validation errors do not duplicate submit errors", () => {
  assert.equal(feedback("not a repository", true, "提交失败").showSubmitError, false);
});
