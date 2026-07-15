import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./ResultsPage.jsx", import.meta.url), "utf8");
const appSource = readFileSync(new URL("../App.jsx", import.meta.url), "utf8");

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
