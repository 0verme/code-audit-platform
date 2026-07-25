import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { getRootNeighborhoodNodeIds } from "@lineage-viewer/domain-adapter";
import { toCycleDependencyGraph, toViewerGraph } from "./lineageAdapter.js";

const graph = {
  rootId: "task:a",
  nodes: [
    { id: "table:source", kind: "table", name: "ODS.SOURCE", displayName: "Source", namespace: "ODS" },
    { id: "task:a", kind: "task", name: "a.py", displayName: "JOB_A", namespace: "python" },
    { id: "table:target", kind: "table", name: "DM.TARGET", displayName: "Target", namespace: "DM" },
  ],
  edges: [
    { id: "1", sourceId: "table:source", targetId: "task:a", kind: "script_reads_table" },
    { id: "2", sourceId: "task:a", targetId: "table:target", kind: "script_writes_table" },
  ],
};

test("lineage graph adapter preserves task and table semantics", () => {
  const viewer = toViewerGraph(graph);
  assert.equal(viewer.nodes.find((node) => node.id === "task:a").type, "job");
  assert.equal(viewer.nodes.find((node) => node.id === "table:source").type, "table");
  assert.equal(viewer.edges[0].source, "table:source");
});

test("lineage graph adapter forwards relationship evidence", () => {
  const viewer = toViewerGraph({
    ...graph,
    edges: [{ ...graph.edges[0], evidence: { type: "parser" }, confidence: 0.9 }],
  });
  assert.deepEqual(viewer.edges[0].metadata.evidence, { type: "parser" });
  assert.equal(viewer.edges[0].metadata.confidence, 0.9);
});

test("root focus includes direct upstream and downstream neighbors", () => {
  assert.deepEqual(getRootNeighborhoodNodeIds(graph).sort(), ["table:source", "table:target", "task:a"]);
});

test("audit host consumes fixed lineage packages without vendor mounting", async () => {
  const [packageJson, canvas] = await Promise.all([
    readFile(new URL("../../../package.json", import.meta.url), "utf8").then(JSON.parse),
    readFile(new URL("./LineageCanvas.jsx", import.meta.url), "utf8"),
  ]);

  assert.equal(packageJson.dependencies["lineage-viewer"], "1.1.0");
  assert.equal(packageJson.dependencies["@lineage-viewer/domain-adapter"], "1.1.0");
  assert.equal(packageJson.dependencies["@lineage-viewer/react"], "1.1.0");
  assert.match(canvas, /@lineage-viewer\/react/);
  assert.doesNotMatch(canvas, /vendor\/lineage-viewer|document\.createElement|replaceChildren/);
});

test("cycle findings merge shared jobs and dependency edges into one graph", () => {
  const cycleGraph = toCycleDependencyGraph([
    { path: "JOB_A → JOB_B → JOB_C → JOB_A" },
    { path: "JOB_C → JOB_A → JOB_C" },
  ]);

  assert.deepEqual(cycleGraph.nodes.map((node) => node.name), ["JOB_A", "JOB_B", "JOB_C"]);
  assert.deepEqual(
    cycleGraph.edges.map((edge) => [edge.sourceId, edge.targetId]),
    [
      ["schedule-job:JOB_A", "schedule-job:JOB_B"],
      ["schedule-job:JOB_B", "schedule-job:JOB_C"],
      ["schedule-job:JOB_C", "schedule-job:JOB_A"],
      ["schedule-job:JOB_A", "schedule-job:JOB_C"],
    ],
  );
  assert.ok(cycleGraph.nodes.every((node) => node.status === "error"));
});

test("cycle graph preserves self dependencies and skips findings without a path", () => {
  const cycleGraph = toCycleDependencyGraph([
    { path: "JOB_SELF -> JOB_SELF" },
    { path: "" },
  ]);

  assert.equal(cycleGraph.nodes.length, 1);
  assert.equal(cycleGraph.edges.length, 1);
  assert.equal(cycleGraph.edges[0].sourceId, cycleGraph.edges[0].targetId);
  assert.equal(cycleGraph.rootId, "schedule-job:JOB_SELF");
});

test("cycle graph handles missing findings", () => {
  assert.deepEqual(toCycleDependencyGraph(), { rootId: "", nodes: [], edges: [] });
});
