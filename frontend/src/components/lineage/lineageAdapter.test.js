import assert from "node:assert/strict";
import test from "node:test";
import { toViewerGraph } from "./lineageAdapter.js";
import { getRootNeighborhoodNodeIds } from "./lineageViewport.js";

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

test("root focus includes direct upstream and downstream neighbors", () => {
  assert.deepEqual(getRootNeighborhoodNodeIds(graph).sort(), ["table:source", "table:target", "task:a"]);
});
