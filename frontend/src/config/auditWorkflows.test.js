import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  buildAuditSubmitPayload,
  canSubmitAudit,
  detectWorkflow,
} from "./auditWorkflows.js";
import {
  GIT_SOURCE_UNSUPPORTED_MESSAGE,
  detectAuditSource,
  inferAuditSourceType,
  normalizeAuditSourceType,
  resolveAuditSourceMeta,
} from "./auditSources.js";

const homeCss = readFileSync(new URL("../styles/home.css", import.meta.url), "utf8");

function cssRule(selector) {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = homeCss.match(new RegExp(`${escapedSelector}\\s*\\{([^}]*)\\}`));
  assert.ok(match, `Missing CSS rule for ${selector}`);
  return match[1];
}

test("hcyt repository path is detected as HCYT", () => {
  assert.equal(detectWorkflow("svn+ssh://svn.example.com/example/repo/branches/demo-hcyt"), "hcyt");
  assert.equal(detectWorkflow("svn+ssh://svn.example.com/repos/branches/demo-hcyt"), "hcyt");
});

test("fine-report repository path is detected as FineReport", () => {
  assert.equal(detectWorkflow("https://git.example.com/report/fine-report.git"), "fine-report");
});

test("nups repository path is detected as NUPS", () => {
  assert.equal(detectWorkflow("svn+ssh://svn.example.com/example/repo/trunk/nups"), "nups");
  assert.equal(detectWorkflow("svn+ssh://svn.example.com/NUPS"), "nups");
  assert.equal(detectWorkflow("svn+ssh://svn.example.com/pay/nups/统一报送"), "nups");
});

test("unmatched repository path returns null", () => {
  assert.equal(detectWorkflow("svn+ssh://svn.example.com/repos/branches/unknown-module"), null);
});

test("unmatched repository path cannot be submitted", () => {
  assert.equal(canSubmitAudit("svn+ssh://svn.example.com/repos/branches/unknown-module"), false);
  assert.equal(buildAuditSubmitPayload({ path: "svn+ssh://svn.example.com/repos/branches/unknown-module" }), null);
});

test("svn repository path submit payload contains workflow and type", () => {
  assert.deepEqual(
    buildAuditSubmitPayload({
      path: "svn://svn.example.com/report/fine-report",
      ai: true,
      dbg: true,
    }),
    {
      path: "svn://svn.example.com/report/fine-report",
      sourceType: "svn",
      ai: true,
      dbg: true,
      workflow: "fine-report",
      type: "fine-report",
    },
  );
});

test("svn path is detected as svn source", () => {
  const source = detectAuditSource("svn+ssh://svn.example.com/repos/branches/demo-hcyt");
  assert.equal(source.sourceType, "svn");
  assert.equal(source.label, "SVN");
  assert.equal(source.tag, "SVN");
  assert.equal(source.valid, true);
});

test("https git path is detected and blocked as unsupported", () => {
  const source = detectAuditSource("https://git.example.com/report/fine-report.git");
  assert.equal(source.sourceType, "git");
  assert.equal(source.label, "Git（暂不支持）");
  assert.equal(source.tag, "Unsupported");
  assert.equal(source.valid, false);
  assert.equal(source.reason, GIT_SOURCE_UNSUPPORTED_MESSAGE);
  assert.equal(canSubmitAudit("https://git.example.com/report/fine-report.git"), false);
  assert.equal(buildAuditSubmitPayload({ path: "https://git.example.com/report/fine-report.git" }), null);
});

test("windows local path is detected as local directory", () => {
  assert.equal(detectAuditSource("C:\\path\\to\\local-hcyt-workspace", { enableLocalSource: true }).sourceType, "local");
});

test("linux local path is detected as local directory", () => {
  assert.equal(detectAuditSource("/home/dev/local-hcyt-workspace", { enableLocalSource: true }).sourceType, "local");
});

test("relative local paths are detected as local directory", () => {
  assert.equal(detectAuditSource("./local-hcyt-workspace", { enableLocalSource: true }).sourceType, "local");
  assert.equal(detectAuditSource("../local-hcyt-workspace", { enableLocalSource: true }).sourceType, "local");
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
      sourceType: "local",
      ai: false,
      dbg: false,
      workflow: "hcyt",
      type: "hcyt",
    },
  );
});

test("git ssh paths are detected and blocked while svn+ssh remains available", () => {
  assert.equal(inferAuditSourceType("ssh://git.example.com/team/repo.git"), "git");
  const source = detectAuditSource("git@gitlab.example.com:team/repo.git");
  assert.equal(source.sourceType, "git");
  assert.equal(source.valid, false);
  assert.equal(source.reason, GIT_SOURCE_UNSUPPORTED_MESSAGE);
  assert.equal(canSubmitAudit("git@gitlab.example.com:team/repo.git"), false);
  assert.equal(inferAuditSourceType("svn+ssh://svn.example.com/project/branch"), "svn");
});

test("selfcheck and legacy source types normalize correctly", () => {
  assert.equal(inferAuditSourceType("local-selfcheck/fine-report"), "selfcheck");
  assert.equal(normalizeAuditSourceType("local_dir"), "local");
});

test("recent task source metadata can be resolved from legacy fields", () => {
  const source = resolveAuditSourceMeta({
    repo: "https://git.example.com/report/fine-report.git",
    source_type: "",
  }, { enableLocalSource: true });

  assert.equal(source.sourceRef, "https://git.example.com/report/fine-report.git");
  assert.equal(source.sourceType, "git");
  assert.equal(source.tag, "Unsupported");
  assert.equal(source.valid, false);
  assert.equal(source.reason, GIT_SOURCE_UNSUPPORTED_MESSAGE);
});

test("source type detection and workflow detection are independent", () => {
  assert.equal(detectAuditSource("svn+ssh://svn.example.com/repos/branches/demo-hcyt").sourceType, "svn");
  assert.equal(detectWorkflow("svn+ssh://svn.example.com/repos/branches/demo-hcyt"), "hcyt");
  assert.equal(detectAuditSource("https://git.example.com/team/nups.git").sourceType, "git");
  assert.equal(detectWorkflow("https://git.example.com/team/nups.git"), "nups");
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
