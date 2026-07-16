import assert from "node:assert/strict";
import test from "node:test";
import {
  getCycleDependencyFindings,
  getPythonIssueRows,
  getScheduleIssuesByTable,
  getScheduleIssueRows,
  getScheduleTableRows,
  hasScheduleTables,
} from "./hcytResultPresentation.js";

const normalDependencies = [{ lane: "上游 / 调度依赖表", nodes: [{ name: "DM.TABLE_A" }] }];

test("normal dependencies do not create a cycle dependency finding", () => {
  const data = { deps: normalDependencies, schedule: { summary: { cycles: 0 }, rows: [{ rule: "重试次数", level: "warn" }] } };

  assert.deepEqual(getCycleDependencyFindings(data), []);
  assert.equal(getScheduleIssueRows(data).length, 1);
});

test("schedule findings are grouped below their PLAN, SEQ, and JOB tables", () => {
  const data = {
    schedule: {
      rows: [
        { table: "plan", level: "err", msg: "plan error" },
        { table: " SEQ ", level: "warn", msg: "seq warning" },
        { table: "JOB", level: "err", msg: "job error" },
        { table: "SCHEDULE", level: "warn", msg: "legacy warning" },
        { level: "err", msg: "unclassified error" },
        { table: "PLAN", level: "ok", msg: "passed" },
      ],
    },
  };

  const grouped = getScheduleIssuesByTable(data);

  assert.deepEqual(grouped.plan.map((row) => row.msg), ["plan error"]);
  assert.deepEqual(grouped.seq.map((row) => row.msg), ["seq warning"]);
  assert.deepEqual(grouped.job.map((row) => row.msg), [
    "job error",
    "legacy warning",
    "unclassified error",
  ]);
});

test("schedule finding groups are safe when report rows are missing", () => {
  assert.deepEqual(getScheduleIssuesByTable({}), { plan: [], seq: [], job: [] });
  assert.deepEqual(getScheduleIssuesByTable({ schedule: { rows: null } }), { plan: [], seq: [], job: [] });
});

test("cycle detail renders a normalized cycle path", () => {
  const data = {
    schedule: {
      summary: { cycles: 1 },
      rows: [{ table: "JOB", rule: "循环依赖检测", level: "err", msg: "作业依赖成环，请检查: JOB_A -> JOB_B -> JOB_C -> JOB_A" }],
    },
  };

  assert.deepEqual(getCycleDependencyFindings(data).map((item) => item.path), ["JOB_A → JOB_B → JOB_C → JOB_A"]);
});

test("historical reports without cycle fields remain safe", () => {
  assert.deepEqual(getCycleDependencyFindings({ schedule: { rows: [] } }), []);
  assert.deepEqual(getCycleDependencyFindings({}), []);
});

test("schedule tables remain visible when every schedule rule passes", () => {
  const data = {
    schedule: {
      rows: [],
      tables: {
        plan: { rows: [["PLAN_A"]] },
        job: { rows: [["JOB_A"]] },
      },
    },
  };

  assert.equal(hasScheduleTables(data), true);
  assert.equal(hasScheduleTables({ schedule: { tables: {} } }), false);
});

test("PLAN, SEQ, and JOB tables sort stably by plan name", () => {
  for (const tableKey of ["plan", "seq", "job"]) {
    const entries = getScheduleTableRows(tableKey, {
      rows: [
        ["PLAN_B", "first B"],
        ["PLAN_A", "first A"],
        ["PLAN_A", "second A"],
      ],
    });

    assert.deepEqual(entries.map(({ row }) => row), [
      ["PLAN_A", "first A"],
      ["PLAN_A", "second A"],
      ["PLAN_B", "first B"],
    ]);
  }
});

test("JOB row states remain attached while empty plan names sort last", () => {
  const entries = getScheduleTableRows("job", {
    rows: [["", "JOB_EMPTY"], ["PLAN_B", "JOB_B"], ["PLAN_A", "JOB_A"]],
    rowStates: ["disabled", "", "new"],
  });

  assert.deepEqual(entries.map(({ row, state }) => [row[1], state]), [
    ["JOB_A", "new"],
    ["JOB_B", ""],
    ["JOB_EMPTY", "disabled"],
  ]);
});

test("CALE rows keep their source order and missing table data is safe", () => {
  const rows = [["2026-07-17"], ["2026-07-16"]];

  assert.deepEqual(getScheduleTableRows("cale", { rows }).map(({ row }) => row), rows);
  assert.deepEqual(getScheduleTableRows("plan", {}), []);
  assert.deepEqual(getScheduleTableRows("seq"), []);
});

test("python counts only script findings and retains script drill-down data", () => {
  const data = {
    refTables: [{ name: "DM.RESULT", type: "result" }],
    pyScripts: [{ script: "load.py", lint: [], result: [{ sql: "DM.RESULT", state: "same" }] }],
  };

  assert.deepEqual(getPythonIssueRows(data), []);
  assert.equal(data.pyScripts[0].result[0].sql, "DM.RESULT");
});
