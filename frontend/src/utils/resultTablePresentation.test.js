import assert from "node:assert/strict";
import test from "node:test";
import {
  formatSqlReference,
  sortReferenceTableNames,
} from "./resultTablePresentation.js";

test("结果表使用全角括号标注来源系统", () => {
  assert.equal(
    formatSqlReference("DWF.F_EVT_COMC_HOLIDAY", { sysNames: ["核心CBS库"] }),
    "DWF.F_EVT_COMC_HOLIDAY（核心CBS库）",
  );
});

test("结果表保留禁用标注和多个来源系统", () => {
  assert.equal(
    formatSqlReference("DWF.F_PTY_COM_INFO", { disabled: true, sysNames: ["老信贷系统", "核心CBS库"] }),
    "DWF.F_PTY_COM_INFO（禁用/老信贷系统/核心CBS库）",
  );
});

test("无标注的结果表仅显示表名", () => {
  assert.equal(formatSqlReference("DWF.F_PTY_ORG", {}), "DWF.F_PTY_ORG");
});

test("临时表名称使用忽略大小写的自然升序", () => {
  assert.deepEqual(
    sortReferenceTableNames([
      "DWM.CRDT_LMT_TEMP_10",
      "dwm.crdt_lmt_temp_2",
      "DWM.CRDT_LMT_TEMP_1",
    ]),
    [
      "DWM.CRDT_LMT_TEMP_1",
      "dwm.crdt_lmt_temp_2",
      "DWM.CRDT_LMT_TEMP_10",
    ],
  );
});

test("临时表名称相同时保持原顺序且不修改输入数组", () => {
  const input = [
    "DWM.CRDT_LMT_TEMP_2",
    "dwm.crdt_lmt_temp_2",
    "DWM.CRDT_LMT_TEMP_1",
  ];
  const original = [...input];

  assert.deepEqual(sortReferenceTableNames(input), [
    "DWM.CRDT_LMT_TEMP_1",
    "DWM.CRDT_LMT_TEMP_2",
    "dwm.crdt_lmt_temp_2",
  ]);
  assert.deepEqual(input, original);
});
