import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./ResultsPage.jsx", import.meta.url), "utf8");
const appSource = readFileSync(new URL("../App.jsx", import.meta.url), "utf8");
const styleSource = readFileSync(new URL("../styles/script-audit.css", import.meta.url), "utf8");
const resultsStyleSource = readFileSync(new URL("../styles/results.css", import.meta.url), "utf8");

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
