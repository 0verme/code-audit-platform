import assert from "node:assert/strict";
import test from "node:test";
import { auditSourceDisplayRules } from "../config/auditSourceDisplayConfig.js";
import {
  findMatchedDisplayRule,
  formatAuditSourceDisplay,
  normalizePathForMatch,
  normalizeSourceType,
} from "./auditSourceDisplay.js";

test("normalizeSourceType handles mixed-case local svn and git values", () => {
  assert.equal(normalizeSourceType("Local"), "local");
  assert.equal(normalizeSourceType("svn"), "svn");
  assert.equal(normalizeSourceType("GIT"), "git");
});

test("normalizePathForMatch normalizes slash style for matching", () => {
  assert.equal(
    normalizePathForMatch("C:\\workspace\\code-audit-platform\\hcyt"),
    "c:/workspace/code-audit-platform/hcyt",
  );
});

test("formatAuditSourceDisplay compacts local paths when prefix matches", () => {
  const result = formatAuditSourceDisplay(
    "C:\\workspace\\code-audit-platform\\hcyt",
    "Local",
    auditSourceDisplayRules,
  );

  assert.deepEqual(result, {
    displayText: "…\\hcyt",
    fullText: "C:\\workspace\\code-audit-platform\\hcyt",
    matched: true,
  });
});

test("formatAuditSourceDisplay compacts svn urls when prefix matches", () => {
  const result = formatAuditSourceDisplay(
    "svn://example.com/repos/branches/demo-hcyt",
    "SVN",
    auditSourceDisplayRules,
  );

  assert.equal(result.displayText, "…/demo-hcyt");
  assert.equal(result.fullText, "svn://example.com/repos/branches/demo-hcyt");
  assert.equal(result.matched, true);
});

test("formatAuditSourceDisplay compacts git urls when prefix matches", () => {
  const result = formatAuditSourceDisplay(
    "https://git.example.com/group/project/repo.git",
    "Git",
    auditSourceDisplayRules,
  );

  assert.equal(result.displayText, "…/repo.git");
  assert.equal(result.fullText, "https://git.example.com/group/project/repo.git");
  assert.equal(result.matched, true);
});

test("formatAuditSourceDisplay keeps the original value when no rule matches", () => {
  const result = formatAuditSourceDisplay(
    "https://git.other.example.com/group/project/repo.git",
    "Git",
    auditSourceDisplayRules,
  );

  assert.equal(result.displayText, "https://git.other.example.com/group/project/repo.git");
  assert.equal(result.fullText, "https://git.other.example.com/group/project/repo.git");
  assert.equal(result.matched, false);
});

test("findMatchedDisplayRule prefers the longest matching prefix", () => {
  const result = findMatchedDisplayRule(
    "C:/workspace/code-audit-platform/hcyt",
    "local",
    auditSourceDisplayRules,
  );

  assert.equal(result?.prefix, "C:\\workspace\\code-audit-platform\\");
  assert.equal(result?.replacement, "…\\");
});

test("formatAuditSourceDisplay preserves raw suffix separator style for default replacements", () => {
  const result = formatAuditSourceDisplay(
    "C:\\workspace\\demo",
    "LOCAL",
    [{ sourceType: "local", prefix: "C:/workspace/" }],
  );

  assert.equal(result.displayText, "…\\demo");
  assert.equal(result.fullText, "C:\\workspace\\demo");
  assert.equal(result.matched, true);
});
