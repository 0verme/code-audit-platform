import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { sortAlertRows } from "./alertSorting.js";

test("alert rows sort by info, warn, err, ok before unknown levels", () => {
  const rows = [
    { level: "unknown", rule: "未知" },
    { level: "ok", rule: "通过" },
    { level: "err", rule: "错误" },
    { level: "info", rule: "提示" },
    { level: "warn", rule: "警告" },
  ];

  assert.deepEqual(
    sortAlertRows(rows).map((row) => row.level),
    ["info", "warn", "err", "ok", "unknown"],
  );
});

test("alert rows use natural Chinese rule ordering and put empty rules last", () => {
  const rows = [
    { level: "warn", rule: "" },
    { level: "warn", rule: "规则10" },
    { level: "warn", rule: "创建视图" },
    { level: "warn", rule: "规则2" },
  ];

  assert.deepEqual(
    sortAlertRows(rows).map((row) => row.rule),
    ["创建视图", "规则2", "规则10", ""],
  );
});

test("alert sorting is stable and does not mutate the source array", () => {
  const first = { id: "first", level: "warn", rule: "同一规则" };
  const second = { id: "second", level: "warn", rule: "同一规则" };
  const rows = [first, second];
  const sorted = sortAlertRows(rows);

  assert.notEqual(sorted, rows);
  assert.deepEqual(sorted, [first, second]);
  assert.deepEqual(rows, [first, second]);
  assert.deepEqual(sortAlertRows(null), []);
});

test("HCYT, NUPS, and FineReport rule-alert renderers use the shared sorter", () => {
  const uiSource = readFileSync(new URL("../components/ui.jsx", import.meta.url), "utf8");
  const resultsSource = readFileSync(new URL("../pages/ResultsPage.jsx", import.meta.url), "utf8");
  const scriptSource = readFileSync(new URL("../pages/ScriptAudit.jsx", import.meta.url), "utf8");
  const nupsSource = readFileSync(new URL("../pages/NupsPage.jsx", import.meta.url), "utf8");
  const fineSource = readFileSync(new URL("../pages/FineReportPage.jsx", import.meta.url), "utf8");

  assert.match(uiSource, /const sortedRows = sortAlertRows\(rows\)/);
  assert.match(resultsSource, /rows\.length \? sortAlertRows\(rows\)/);
  assert.match(resultsSource, /const sortedRows = sortAlertRows\(rows\)/);
  assert.match(resultsSource, /return sortAlertRows\(groups\.flatMap/);
  assert.match(scriptSource, /const lint = sortAlertRows\(script\?\.lint\)/);
  assert.match(nupsSource, /<ViolationTable rows=\{rows\} cols=\{NUPS_MESSAGE_COLUMNS\} \/>/);
  assert.match(fineSource, /const sortedMessages = sortAlertRows\(messages\)/);
  assert.match(fineSource, /const issues = sortAlertRows\(report\.issues\)/);
});
