import assert from "node:assert/strict";
import test from "node:test";

import {
  FINE_REPORT_REF_TABLE_GROUPS,
  groupFineReportRefTables,
} from "./fineReportPresentation.js";

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
