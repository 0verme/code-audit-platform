import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { shouldDefaultOpenChangeList } from "../utils/changeListPresentation.js";
import {
  getScriptElementId,
  getScriptKey,
} from "../utils/scriptAuditPresentation.js";

const source = [
  readFileSync(new URL("./ResultsPage.jsx", import.meta.url), "utf8"),
  readFileSync(new URL("../components/results/HcytRunProgress.jsx", import.meta.url), "utf8"),
].join("\n");
const nupsSource = readFileSync(new URL("./NupsPage.jsx", import.meta.url), "utf8");
const appSource = [
  readFileSync(new URL("../App.jsx", import.meta.url), "utf8"),
  readFileSync(new URL("../components/app/ResultRail.jsx", import.meta.url), "utf8"),
].join("\n");
const navigationSource = readFileSync(new URL("../config/resultNavigation.js", import.meta.url), "utf8");
const styleSource = readFileSync(new URL("../styles/script-audit.css", import.meta.url), "utf8");
const resultsStyleSource = readFileSync(new URL("../styles/results.css", import.meta.url), "utf8");
const uiSource = readFileSync(new URL("../components/ui.jsx", import.meta.url), "utf8");
const sharedStyleSource = readFileSync(new URL("../styles/styles.css", import.meta.url), "utf8");
const changeFilesSource = readFileSync(new URL("../components/results/ChangeFilesSection.jsx", import.meta.url), "utf8");
const sharedSectionsSource = readFileSync(new URL("../components/results/SharedResultSections.jsx", import.meta.url), "utf8");
const accordionHookSource = readFileSync(new URL("../hooks/useAutoOpenAccordion.js", import.meta.url), "utf8");

test("change lists default to collapsed only when they contain more than ten files", () => {
  assert.equal(shouldDefaultOpenChangeList(0), true);
  assert.equal(shouldDefaultOpenChangeList(1), true);
  assert.equal(shouldDefaultOpenChangeList(10), true);
  assert.equal(shouldDefaultOpenChangeList(11), false);
  assert.equal(shouldDefaultOpenChangeList(98), false);
  assert.match(changeFilesSource, /defaultOpen=\{shouldDefaultOpenChangeList\(changes\.length\)\}/);
  assert.match(source, /<ChangeFilesSection changes=\{mergedData\.changes\}/);
  assert.match(nupsSource, /<ChangeFilesSection changes=\{getNupsChanges\(d\)\}/);
});

test("change list and SQL check use the report download URL as a direct link", () => {
  assert.match(changeFilesSource, /href=\{change\.downloadUrl\}[\s\S]*?target="_blank"/);
  assert.match(source, /href=\{scriptMeta\.downloadUrl\}[\s\S]*?target="_blank"/);
});

test("SQL downloads preserve the server attachment response instead of creating a Blob URL", () => {
  assert.doesNotMatch(source, /downloadSourceFile|resolveSourceDownloadUrl|URL\.createObjectURL|fetch\(/);
});

test("module progress board covers all twelve backend tasks", () => {
  const taskBlock = source.slice(
    source.indexOf("const MODULE_TASKS"),
    source.indexOf("const TASK_STATUS_META"),
  );
  const keys = [...taskBlock.matchAll(/key:\s*"([^"]+)"/g)].map((match) => match[1]);
  assert.equal(keys.length, 12);
  assert.deepEqual(keys.slice(-2), ["lineage", "summary"]);
  assert.match(taskBlock, /key:\s*"source_load"/);
  assert.match(taskBlock, /label:\s*"保存审查报告"/);
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
  assert.match(source, /useAutoOpenAccordion\(\{/);
  assert.match(accordionHookSource, /dismissedIds\.add\(itemId\)/);
  assert.match(accordionHookSource, /dismissedIds\.delete\(itemId\)/);
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

test("Python script navigation prefers paths while retaining filename compatibility", () => {
  const nestedScript = { script: "load.py", path: "jobs/daily/load.py", lint: [{ level: "err" }], result: [] };
  const legacyScript = { script: "legacy.py", lint: [{ level: "warn" }], result: [] };

  assert.equal(getScriptKey(nestedScript), "jobs/daily/load.py");
  assert.equal(getScriptKey(legacyScript), "legacy.py");
  assert.equal(getScriptElementId(nestedScript), "python-script-jobs%2Fdaily%2Fload.py");
});

test("Python navigation renders every script as an expanded nested directory", () => {
  const scriptSource = readFileSync(new URL("./ScriptAudit.jsx", import.meta.url), "utf8");

  assert.match(appSource, /useState\(\s*\(\) =>\s*new Set\(\["python", "reports"\]\)\s*,?\s*\)/);
  assert.match(
    appSource,
    /const nestedItems = isPython[\s\S]*?\? pythonScripts[\s\S]*?: isReports[\s\S]*?\? fineReports[\s\S]*?: null/,
  );
  assert.match(
    appSource,
    /const isActive = isPython[\s\S]*?\? activeScriptKey === itemKey[\s\S]*?: activeReportKey === itemKey/,
  );
  assert.match(appSource, /const itemTitle = isPython[\s\S]*?\? item\.script/);
  assert.match(
    appSource,
    /isPython[\s\S]*?\? onJumpScript\(item\)[\s\S]*?: onJumpReport\(item\)/,
  );
  assert.match(accordionHookSource, /document[\s\S]*getElementById\(getElementId\(itemKey\)\)[\s\S]*scrollIntoView/);
  assert.match(scriptSource, /id=\{scriptElementId\}/);
  assert.match(sharedStyleSource, /\.nav-child-label \{[\s\S]*text-overflow: ellipsis/);
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
  assert.match(lineagePage, /Python 数据血缘/);
  assert.match(lineagePage, /rootKey: selection\.lineageKey/);
  assert.doesNotMatch(lineagePage, /direction|depth|maxNodes/);
  assert.doesNotMatch(lineagePage, /节点已达 100 个上限/);
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
  assert.match(sharedSectionsSource, /id="asset-issues"[\s\S]*?accentHeader/);
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
  assert.match(navigationSource, /id: "asset-issues"/);
  assert.match(sharedSectionsSource, /id="asset-issues"/);
});

test("SCHEMA_CONFIG details expand inline instead of using a separate panel", () => {
  assert.match(source, /<ConfigCheckSection rows=\{mergedData\.config\} files=\{mergedData\.configFiles\} sourceFiles=\{getSourceFiles\(mergedData, "config"\)\} reg=\{reg\} \/>/);
  assert.doesNotMatch(source, /id="configjson"|function ConfigJsonSection/);
  assert.match(source, /const \[openRowIndex, setOpenRowIndex\] = useState\(null\)/);
  assert.match(source, /aria-expanded=\{isOpen\}/);
  assert.match(source, /aria-controls=\{detailId\}/);
  assert.match(source, /onClick=\{canExpand \? \(\) => toggleRow\(rowIndex\) : undefined\}/);
  assert.match(source, /const canExpand = isSchemaConfig && \(files\.length > 0 \|\| sourceFiles\.length > 0\)/);
  assert.match(source, /rows\.length \? sortAlertRows\(rows\) : \[\{[\s\S]*?file: "SCHEMA_CONFIG"[\s\S]*?level: "ok"/);
  assert.match(source, /files\.map\(\(file, fileIndex\)/);
  assert.match(source, /暂未生成可展示的解析明细/);
  assert.match(resultsStyleSource, /\.config-check-row\.open \.config-row-chev \{ transform: rotate\(90deg\); \}/);
});

test("HCYT file-backed sections expose source downloads even without findings", () => {
  assert.match(source, /!rows\.length && !scriptMeta\?\.script && !sourceFiles\.length/);
  assert.match(source, /sourceFiles=\{getSourceFiles\(mergedData, "sbin"\)\}/);
  assert.match(source, /sourceFiles=\{getSourceFiles\(mergedData, "recv"\)\}/);
  assert.match(source, /function OtherSourceFilesSection/);
  assert.match(source, /source\?\.downloadUrl/);
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
