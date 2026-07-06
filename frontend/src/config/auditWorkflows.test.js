import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  buildAuditSubmitPayload,
  canSubmitAudit,
  detectWorkflow,
} from "./auditWorkflows.js";
import { detectAuditSource } from "./auditSources.js";

const homeCss = readFileSync(new URL("../styles/home.css", import.meta.url), "utf8");

function cssRule(selector) {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = homeCss.match(new RegExp(`${escapedSelector}\\s*\\{([^}]*)\\}`));
  assert.ok(match, `Missing CSS rule for ${selector}`);
  return match[1];
}

test("hcyt repository path is detected as HCYT", () => {
  assert.equal(detectWorkflow("svn://10.18.32.7/datawh/branches/202602/hcyt"), "hcyt");
  assert.equal(detectWorkflow("svn://example.com/repos/branches/demo-hcyt"), "hcyt");
});

test("fine-report repository path is detected as FineReport", () => {
  assert.equal(detectWorkflow("https://git.intra/report/fine-report.git"), "fine-report");
});

test("nups repository path is detected as NUPS", () => {
  assert.equal(detectWorkflow("svn://10.18.32.7/pay/nups/trunk"), "nups");
  assert.equal(detectWorkflow("svn://example.com/NUPS"), "nups");
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
      ai: true,
      dbg: true,
    }),
    {
      path: "https://git.intra/report/fine-report.git",
      sourceType: "git",
      ai: true,
      dbg: true,
      workflow: "fine-report",
      type: "fine-report",
    },
  );
});

test("svn path is detected as svn source", () => {
  assert.deepEqual(detectAuditSource("svn://example.com/repos/branches/demo-hcyt"), {
    sourceType: "svn",
    label: "svn",
    valid: true,
  });
});

test("https git path is detected as git source", () => {
  assert.deepEqual(detectAuditSource("https://git.intra/report/fine-report.git"), {
    sourceType: "git",
    label: "git",
    valid: true,
  });
});

test("windows local path is detected as local directory", () => {
  assert.equal(detectAuditSource("C:\\path\\to\\local-hcyt-workspace", { enableLocalSource: true }).sourceType, "local_dir");
});

test("linux local path is detected as local directory", () => {
  assert.equal(detectAuditSource("/home/dev/local-hcyt-workspace", { enableLocalSource: true }).sourceType, "local_dir");
});

test("relative local paths are detected as local directory", () => {
  assert.equal(detectAuditSource("./local-hcyt-workspace", { enableLocalSource: true }).sourceType, "local_dir");
  assert.equal(detectAuditSource("../local-hcyt-workspace", { enableLocalSource: true }).sourceType, "local_dir");
});

test("unknown path cannot be submitted", () => {
  const source = detectAuditSource("plain random string");
  assert.equal(source.sourceType, "unknown");
  assert.equal(source.valid, false);
  assert.equal(canSubmitAudit("plain random string"), false);
});

test("local directory cannot be submitted when local source is disabled", () => {
  assert.equal(detectAuditSource("C:\\path\\to\\local-hcyt-workspace", { enableLocalSource: false }).valid, false);
  assert.equal(canSubmitAudit("C:\\path\\to\\local-hcyt-workspace", { enableLocalSource: false }), false);
  assert.equal(buildAuditSubmitPayload({ path: "C:\\path\\to\\local-hcyt-workspace", enableLocalSource: false }), null);
});

test("local directory can be submitted in development or when explicitly enabled", () => {
  assert.equal(canSubmitAudit("C:\\path\\to\\local-hcyt-workspace", { dev: true }), true);
  assert.deepEqual(
    buildAuditSubmitPayload({
      path: "C:\\path\\to\\local-hcyt-workspace",
      enableLocalSource: true,
    }),
    {
      path: "C:\\path\\to\\local-hcyt-workspace",
      sourceType: "local_dir",
      ai: false,
      dbg: false,
      workflow: "hcyt",
      type: "hcyt",
    },
  );
});

test("source type detection and workflow detection are independent", () => {
  assert.equal(detectAuditSource("svn://example.com/repos/branches/demo-hcyt").sourceType, "svn");
  assert.equal(detectWorkflow("svn://example.com/repos/branches/demo-hcyt"), "hcyt");
  assert.equal(detectAuditSource("https://git.intra/team/nups.git").sourceType, "git");
  assert.equal(detectWorkflow("https://git.intra/team/nups.git"), "nups");
});

test("workflow card grid uses bounded responsive columns", () => {
  const routeGridRule = cssRule(".route-grid");

  assert.match(routeGridRule, /grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(min\(220px,\s*100%\),\s*1fr\)\)/);
  assert.match(routeGridRule, /max-width:\s*100%/);
  assert.match(routeGridRule, /min-width:\s*0/);
  assert.match(routeGridRule, /box-sizing:\s*border-box/);
});

test("workflow cards and text cannot widen beyond the parent container", () => {
  const cardRule = cssRule(".route-card");
  const bodyRule = cssRule(".rc-body");
  const textRule = cssRule(".rc-name,\n.rc-kw,\n.rc-desc");

  assert.match(cardRule, /min-width:\s*0/);
  assert.match(cardRule, /max-width:\s*100%/);
  assert.match(cardRule, /box-sizing:\s*border-box/);
  assert.match(cardRule, /overflow:\s*hidden/);
  assert.match(bodyRule, /min-width:\s*0/);
  assert.match(bodyRule, /max-width:\s*100%/);
  assert.match(textRule, /overflow:\s*hidden/);
  assert.match(textRule, /text-overflow:\s*ellipsis/);
  assert.match(textRule, /white-space:\s*nowrap/);
});

test("recognized workflow card state does not change card dimensions", () => {
  const activeRule = cssRule(".route-card.active");

  assert.doesNotMatch(activeRule, /\b(width|min-width|max-width|padding|margin|grid-column|flex-basis)\s*:/);
});
