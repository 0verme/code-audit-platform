import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { shouldDefaultOpenChangeList } from "../utils/changeListPresentation.js";

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
  assert.match(source, /const \[openScriptIds, setOpenScriptIds\] = useState\(\(\) => new Set\(/);
  assert.match(source, /filter\(\(script\) => \{[\s\S]*return audit\.err \|\| audit\.warn/);
  assert.match(source, /map\(\(script\) => script\.script\)/);
  assert.match(source, /<PyScriptAuditSection d=\{mergedData\} reg=\{reg\} openScriptIds=\{openScriptIds\} onToggle=\{toggleScript\}/);
  assert.doesNotMatch(source, /ScriptDetailDrawer/);
  assert.match(scriptSource, /aria-expanded=\{isOpen\}/);
  assert.match(scriptSource, /ScriptDetailAccordion script=\{script\} detailId=\{detailId\}/);
  assert.doesNotMatch(scriptSource, /sd-overlay|sd-drawer/);
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

test("SCHEMA_CONFIG details expand inline instead of using a separate panel", () => {
  assert.match(source, /<ConfigCheckSection rows=\{mergedData\.config\} files=\{mergedData\.configFiles\} reg=\{reg\} \/>/);
  assert.doesNotMatch(source, /id="configjson"|function ConfigJsonSection/);
  assert.match(source, /const \[openRowIndex, setOpenRowIndex\] = useState\(null\)/);
  assert.match(source, /aria-expanded=\{isOpen\}/);
  assert.match(source, /aria-controls=\{detailId\}/);
  assert.match(source, /onClick=\{canExpand \? \(\) => toggleRow\(rowIndex\) : undefined\}/);
  assert.match(source, /rows\.length \? rows : \[\{[\s\S]*?file: "SCHEMA_CONFIG"[\s\S]*?level: "ok"/);
  assert.match(source, /files\.map\(\(file, fileIndex\)/);
  assert.match(resultsStyleSource, /\.config-check-row\.open \.config-row-chev \{ transform: rotate\(90deg\); \}/);
});

test("accent panel headers use theme tokens for light and dark mode compatibility", () => {
  assert.match(sharedStyleSource, /\.panel\.accent-header \.panel-head \{[\s\S]*background: var\(--accent-weak\);[\s\S]*border-bottom-color: var\(--accent-line\);/);
  assert.match(sharedStyleSource, /\.panel\.accent-header \.panel-title,[\s\S]*color: var\(--accent\);/);
  assert.match(sharedStyleSource, /\.panel\.accent-header \.panel-ico \{[\s\S]*var\(--accent\)[\s\S]*var\(--surface\)[\s\S]*var\(--accent-line\)/);
  assert.match(sharedStyleSource, /\[data-theme="dark"\] \.panel\.accent-header \.panel-title,[\s\S]*color: color-mix\(in oklab, var\(--accent\) 62%, var\(--text\)\);/);
});
