import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { shouldDefaultOpenChangeList } from "../utils/changeListPresentation.js";
import { syncAutoOpenScriptIds } from "../utils/scriptAuditPresentation.js";

const source = readFileSync(new URL("./ResultsPage.jsx", import.meta.url), "utf8");
const nupsSource = readFileSync(new URL("./NupsPage.jsx", import.meta.url), "utf8");
const appSource = readFileSync(new URL("../App.jsx", import.meta.url), "utf8");
const styleSource = readFileSync(new URL("../styles/script-audit.css", import.meta.url), "utf8");
const resultsStyleSource = readFileSync(new URL("../styles/results.css", import.meta.url), "utf8");
const uiSource = readFileSync(new URL("../components/ui.jsx", import.meta.url), "utf8");
const sharedStyleSource = readFileSync(new URL("../styles/styles.css", import.meta.url), "utf8");

test("change lists default to collapsed only when they contain more than ten files", () => {
  assert.equal(shouldDefaultOpenChangeList(0), true);
  assert.equal(shouldDefaultOpenChangeList(1), true);
  assert.equal(shouldDefaultOpenChangeList(10), true);
  assert.equal(shouldDefaultOpenChangeList(11), false);
  assert.equal(shouldDefaultOpenChangeList(98), false);
  assert.match(source, /defaultOpen=\{shouldDefaultOpenChangeList\(d\.changes\.length\)\}/);
  assert.match(nupsSource, /defaultOpen=\{shouldDefaultOpenChangeList\(changes\.length\)\}/);
});

test("change list and SQL check use the report download URL as a direct link", () => {
  assert.match(source, /href=\{change\.downloadUrl\}[\s\S]*?target="_blank"/);
  assert.match(source, /href=\{scriptMeta\.downloadUrl\}[\s\S]*?target="_blank"/);
});

test("SQL downloads preserve the server attachment response instead of creating a Blob URL", () => {
  assert.doesNotMatch(source, /downloadSourceFile|resolveSourceDownloadUrl|URL\.createObjectURL|fetch\(/);
});

test("execution logs remain the only results-page log entry", () => {
  assert.match(source, /function RunLogs\(\{ d \}\)/);
  assert.match(source, /<RunLogs d=\{mergedData\} \/>/);
  assert.doesNotMatch(appSource, /function DebugConsole\(/);
  assert.doesNotMatch(appSource, /svn_check 实时日志/);
});

test("execution logs can be resized vertically while retaining scroll boundaries", () => {
  assert.match(resultsStyleSource, /\.run-logs pre \{[\s\S]*height: 280px;/);
  assert.match(resultsStyleSource, /\.run-logs pre \{[\s\S]*min-height: 120px;/);
  assert.match(resultsStyleSource, /\.run-logs pre \{[\s\S]*max-height: min\(70vh, 720px\);/);
  assert.match(resultsStyleSource, /\.run-logs pre \{[\s\S]*overflow: auto;/);
  assert.match(resultsStyleSource, /\.run-logs pre \{[\s\S]*resize: vertical;/);
});

test("Python script details use independently expanded inline accordions", () => {
  const scriptSource = readFileSync(new URL("./ScriptAudit.jsx", import.meta.url), "utf8");
  assert.match(source, /syncAutoOpenScriptIds\(new Set\(\), d\.pyScripts, dismissedScriptIds\.current\)/);
  assert.match(source, /syncAutoOpenScriptIds\(current, mergedData\.pyScripts, dismissedScriptIds\.current\)/);
  assert.match(source, /dismissedScriptIds\.current\.add\(scriptId\)/);
  assert.match(source, /dismissedScriptIds\.current\.delete\(scriptId\)/);
  assert.match(source, /<PyScriptAuditSection d=\{mergedData\} reg=\{reg\} openScriptIds=\{openScriptIds\} onToggle=\{toggleScript\}/);
  assert.doesNotMatch(source, /ScriptDetailDrawer/);
  assert.match(scriptSource, /aria-expanded=\{isOpen\}/);
  assert.match(scriptSource, /ScriptDetailAccordion script=\{script\} detailId=\{detailId\}/);
  assert.doesNotMatch(scriptSource, /sd-overlay|sd-drawer/);
});

test("Python script details omit the review focus while FineReport keeps its focus callout", () => {
  const scriptSource = readFileSync(new URL("./ScriptAudit.jsx", import.meta.url), "utf8");
  const fineReportSource = readFileSync(new URL("./FineReportPage.jsx", import.meta.url), "utf8");
  assert.doesNotMatch(scriptSource, /className="sd-focus"/);
  assert.doesNotMatch(scriptSource, /script\.focus/);
  assert.match(fineReportSource, /className="sd-focus"/);
  assert.match(fineReportSource, /report\.focus/);
});

test("Python script findings auto-open after progressive results arrive without overriding manual dismissal", () => {
  const cleanScript = { script: "clean.py", lint: [], result: [] };
  const errorScript = { script: "error.py", lint: [{ level: "err" }], result: [] };
  const warningScript = { script: "warning.py", lint: [{ level: "warn" }], result: [] };

  const initiallyOpen = syncAutoOpenScriptIds(new Set(), [], new Set());
  assert.deepEqual([...initiallyOpen], []);

  const autoOpened = syncAutoOpenScriptIds(initiallyOpen, [cleanScript, errorScript, warningScript], new Set());
  assert.deepEqual([...autoOpened], ["error.py", "warning.py"]);

  const dismissed = new Set(["error.py"]);
  const manuallyClosed = new Set(["warning.py"]);
  const refreshed = syncAutoOpenScriptIds(manuallyClosed, [cleanScript, errorScript, warningScript], dismissed);
  assert.deepEqual([...refreshed], ["warning.py"]);
  assert.equal(syncAutoOpenScriptIds(refreshed, [errorScript, warningScript], dismissed), refreshed);
});

test("each HCYT Python row exposes a separate lineage action", () => {
  const scriptSource = readFileSync(new URL("./ScriptAudit.jsx", import.meta.url), "utf8");
  const lineagePage = readFileSync(new URL("./LineagePage.jsx", import.meta.url), "utf8");
  assert.match(scriptSource, /className="btn ghost sm pas-lineage"/);
  assert.match(scriptSource, /getScriptLineageKey\(script\)/);
  assert.match(scriptSource, /onClick=\{\(\) => onViewLineage\?\.\(\{ \.\.\.script, lineageKey \}\)\}/);
  assert.match(scriptSource, /disabled=\{!lineageEnabled \|\| !lineageKey\}/);
  assert.match(appSource, /setLineageSelection\(script\); setView\("lineage"\)/);
  assert.match(lineagePage, /getAuditTaskLineage/);
  assert.match(lineagePage, /返回审查结果/);
});

test("inline detail accordion uses distinct light and dark card surfaces", () => {
  assert.match(styleSource, /\.detail-accordion-content \{[\s\S]*background: #f5f7ff/);
  assert.match(styleSource, /border-top: 3px solid var\(--accent\)/);
  assert.match(styleSource, /\[data-theme="dark"\] \.detail-accordion-content/);
  assert.match(styleSource, /background: #101a2d/);
  assert.doesNotMatch(styleSource, /\.detail-accordion-content \{[\s\S]*background: var\(--bg\)/);
});

test("HCYT check panels opt into the shared accent header treatment", () => {
  const scriptSource = readFileSync(new URL("./ScriptAudit.jsx", import.meta.url), "utf8");
  assert.match(uiSource, /accentHeader = false/);
  assert.match(uiSource, /accentHeader \? " accent-header" : ""/);
  assert.match(source, /function CheckSection[\s\S]*?<Panel[\s\S]*?accentHeader/);
  assert.match(source, /id="asset-issues"[\s\S]*?accentHeader/);
  assert.match(source, /function ConfigCheckSection[\s\S]*?<Panel[\s\S]*?accentHeader/);
  assert.match(source, /id="schedule"[\s\S]*?accentHeader/);
  assert.match(scriptSource, /id="python"[\s\S]*?accentHeader/);
});

test("schedule findings render inside their PLAN, SEQ, and JOB table blocks", () => {
  assert.match(source, /getScheduleIssuesByTable/);
  assert.match(source, /function ScheduleIssueTable\(\{ rows, columns \}\)/);
  assert.match(source, /key !== "cale" \? <ScheduleIssueTable rows=\{issuesByTable\[key\]\} columns=\{columns\} \/>/);
  assert.match(source, /key === "job" \? <CycleDependencyList findings=\{cycleFindings\} \/>/);
  assert.match(source, /toCycleDependencyGraph\(findings\)/);
  assert.match(source, /<LineageCanvas[\s\S]*?initialFit="view"/);
  assert.match(source, /<LineageCanvas[\s\S]*?showSelfLoops/);
  assert.doesNotMatch(source, /scheduleIssues\.map\(/);
});

test("asset issues are available from the HCYT result navigation", () => {
  assert.match(appSource, /id: "asset-issues", label: "资产问题", icon: "link", get: \(data\) => data\.assetIssues \|\| \[\]/);
  assert.match(source, /id="asset-issues"/);
});

test("SCHEMA_CONFIG details expand inline instead of using a separate panel", () => {
  assert.match(source, /<ConfigCheckSection rows=\{mergedData\.config\} files=\{mergedData\.configFiles\} reg=\{reg\} \/>/);
  assert.doesNotMatch(source, /id="configjson"|function ConfigJsonSection/);
  assert.match(source, /const \[openRowIndex, setOpenRowIndex\] = useState\(null\)/);
  assert.match(source, /aria-expanded=\{isOpen\}/);
  assert.match(source, /aria-controls=\{detailId\}/);
  assert.match(source, /onClick=\{canExpand \? \(\) => toggleRow\(rowIndex\) : undefined\}/);
  assert.match(source, /rows\.length \? sortAlertRows\(rows\) : \[\{[\s\S]*?file: "SCHEMA_CONFIG"[\s\S]*?level: "ok"/);
  assert.match(source, /files\.map\(\(file, fileIndex\)/);
  assert.match(resultsStyleSource, /\.config-check-row\.open \.config-row-chev \{ transform: rotate\(90deg\); \}/);
});

test("audit result tables do not expose line-number fields", () => {
  const scriptSource = readFileSync(new URL("./ScriptAudit.jsx", import.meta.url), "utf8");
  assert.doesNotMatch(uiSource, /label: "行号"|key: "line"/);
  assert.doesNotMatch(source, />行号<|row\.line|row\.line_no|item\.line/);
  assert.doesNotMatch(scriptSource, />行号<|item\.line/);
  assert.match(source, /<td colSpan=\{4\}>/);
});

test("accent panel headers use theme tokens for light and dark mode compatibility", () => {
  assert.match(sharedStyleSource, /\.panel\.accent-header \.panel-head \{[\s\S]*background: var\(--accent-weak\);[\s\S]*border-bottom-color: var\(--accent-line\);/);
  assert.match(sharedStyleSource, /\.panel\.accent-header \.panel-title,[\s\S]*color: var\(--accent\);/);
  assert.match(sharedStyleSource, /\.panel\.accent-header \.panel-ico \{[\s\S]*var\(--accent\)[\s\S]*var\(--surface\)[\s\S]*var\(--accent-line\)/);
  assert.match(sharedStyleSource, /\[data-theme="dark"\] \.panel\.accent-header \.panel-title,[\s\S]*color: color-mix\(in oklab, var\(--accent\) 62%, var\(--text\)\);/);
});

test("structured findings keep ruleCode additive and support all three levels", () => {
  const findings = [
    { ruleCode: "hcyt.sql.invalid_type", rule: "字段类型不合规", level: "err", msg: "错误说明" },
    { ruleCode: "hcyt.config.missing_source", rule: "缺少源配置", level: "warn", msg: "警告说明" },
    { ruleCode: "hcyt.sql.alter_statement", rule: "存在 ALTER 命令", level: "info", msg: "提示说明" },
  ];

  assert.deepEqual(findings.map((item) => item.level), ["err", "warn", "info"]);
  assert.ok(findings.every((item) => item.ruleCode && item.rule && item.msg));
  assert.match(uiSource, /row\[column\.key\]/);
  assert.match(uiSource, /<Sev level=\{row\.level\} \/>/);
  assert.match(source, /row\.rule/);
  assert.match(source, /row\.msg/);
});
