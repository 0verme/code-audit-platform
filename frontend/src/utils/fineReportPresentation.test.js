import assert from "node:assert/strict";
import test from "node:test";

import {
  FINE_REPORT_REF_TABLE_GROUPS,
  groupFineReportRefTables,
  syncAutoOpenReportIds,
} from "./fineReportPresentation.js";

const cleanReport = { file: "clean.cpt", issues: [] };
const errorReport = { file: "error.cpt", issues: [{ level: "err" }] };
const warningReport = { file: "warning.cpt", issues: [{ level: "warn" }] };

test("FineReport findings auto-open after asynchronous results arrive", () => {
  const initiallyOpen = syncAutoOpenReportIds(new Set(), [], new Set());
  assert.deepEqual([...initiallyOpen], []);

  const autoOpened = syncAutoOpenReportIds(
    initiallyOpen,
    [cleanReport, errorReport, warningReport],
    new Set(),
  );
  assert.deepEqual([...autoOpened], ["error.cpt", "warning.cpt"]);
});

test("FineReport auto-open preserves manual dismissal and reopening", () => {
  const dismissed = new Set(["error.cpt"]);
  const manuallyOpen = new Set(["warning.cpt"]);
  const refreshed = syncAutoOpenReportIds(
    manuallyOpen,
    [cleanReport, errorReport, warningReport],
    dismissed,
  );

  assert.deepEqual([...refreshed], ["warning.cpt"]);
  assert.equal(
    syncAutoOpenReportIds(refreshed, [errorReport, warningReport], dismissed),
    refreshed,
  );

  dismissed.delete("error.cpt");
  const reopened = syncAutoOpenReportIds(refreshed, [errorReport, warningReport], dismissed);
  assert.deepEqual([...reopened], ["warning.cpt", "error.cpt"]);
});

test("FineReport auto-open ignores invalid rows and non-actionable issue levels", () => {
  const current = new Set();
  const result = syncAutoOpenReportIds(
    current,
    [null, { issues: [{ level: "err" }] }, { file: "info.cpt", issues: [{ level: "info" }] }],
    new Set(),
  );

  assert.equal(result, current);
});

test("FineReport referenced tables use the result, code-value, and temporary groups", () => {
  assert.deepEqual(
    FINE_REPORT_REF_TABLE_GROUPS.map(({ key, label }) => ({ key, label })),
    [
      { key: "result", label: "结果表" },
      { key: "src", label: "码值表" },
      { key: "mid", label: "中间临时表" },
    ],
  );

  const grouped = groupFineReportRefTables([
    { name: "DM.RESULT_A", type: "result", disabled: true, sysNames: ["核心系统"], highlight: true },
    { name: "DWP.P_CODE_A", type: "src" },
    { name: "DWM.M_STAGE_A", type: "mid" },
    { name: "TMP.SESSION_A", type: "temp" },
    { name: "LEGACY.NO_TYPE", sysNames: ["历史数据"] },
    "LEGACY.STRING_TABLE",
  ]);

  assert.deepEqual(grouped.result, [
    { name: "DM.RESULT_A", type: "result", disabled: true, sysNames: ["核心系统"], highlight: true },
  ]);
  assert.deepEqual(grouped.src, [
    { name: "DWP.P_CODE_A", type: "src" },
  ]);
  assert.deepEqual(grouped.mid, [
    { name: "DWM.M_STAGE_A", type: "mid" },
    { name: "TMP.SESSION_A", type: "mid" },
    { name: "LEGACY.NO_TYPE", type: "mid", sysNames: ["历史数据"] },
    { name: "LEGACY.STRING_TABLE", type: "mid" },
  ]);
});

test("FineReport referenced table groups remain present when empty", () => {
  assert.deepEqual(groupFineReportRefTables(), {
    result: [],
    src: [],
    mid: [],
  });
});
