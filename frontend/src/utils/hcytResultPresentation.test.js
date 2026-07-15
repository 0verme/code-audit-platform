import assert from "node:assert/strict";
import test from "node:test";
import { getCycleDependencyFindings, getPythonIssueRows, getScheduleIssueRows } from "./hcytResultPresentation.js";

const normalDependencies = [{ lane: "上游 / 调度依赖表", nodes: [{ name: "DM.TABLE_A" }] }];

test("normal dependencies do not create a cycle dependency finding", () => {
  const data = { deps: normalDependencies, schedule: { summary: { cycles: 0 }, rows: [{ rule: "重试次数", level: "warn" }] } };

  assert.deepEqual(getCycleDependencyFindings(data), []);
  assert.equal(getScheduleIssueRows(data).length, 1);
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

test("python counts only script findings and retains script drill-down data", () => {
  const data = {
    refTables: [{ name: "DM.RESULT", type: "result" }],
    pyScripts: [{ script: "load.py", lint: [], result: [{ sql: "DM.RESULT", state: "same" }] }],
  };

  assert.deepEqual(getPythonIssueRows(data), []);
  assert.equal(data.pyScripts[0].result[0].sql, "DM.RESULT");
});
