import { toViewerGraph as adaptDomainGraph } from "@lineage-viewer/domain-adapter";

const cycleNodeId = (name) => `schedule-job:${encodeURIComponent(name)}`;

export function toCycleDependencyGraph(findings) {
  const nodes = new Map();
  const edges = new Map();
  let rootId = "";

  for (const finding of findings || []) {
    const names = String(finding?.path || "")
      .split(/\s*(?:→|->)\s*/)
      .map((name) => name.trim())
      .filter(Boolean);

    for (const name of names) {
      const id = cycleNodeId(name);
      if (!rootId) rootId = id;
      if (!nodes.has(id)) {
        nodes.set(id, {
          id,
          kind: "task",
          name,
          displayName: "调度作业",
          namespace: "JOB",
          status: "error",
        });
      }
    }

    for (let index = 0; index < names.length - 1; index += 1) {
      const sourceId = cycleNodeId(names[index]);
      const targetId = cycleNodeId(names[index + 1]);
      const edgeKey = `${sourceId}\u0000${targetId}`;
      if (!edges.has(edgeKey)) {
        edges.set(edgeKey, {
          id: `schedule-dependency:${encodeURIComponent(names[index])}:${encodeURIComponent(names[index + 1])}`,
          sourceId,
          targetId,
          kind: "schedule_dependency",
        });
      }
    }
  }

  return {
    rootId,
    nodes: [...nodes.values()],
    edges: [...edges.values()],
  };
}

export function toViewerGraph(graph) {
  return adaptDomainGraph(graph, {
    nodeTypes: { task: "job", table: "table" },
    edgeTypes: (edge) => edge.kind === "schedule_dependency" ? "dependency" : "lineage",
    maxLabelLength: 28,
    maxSubtitleLength: 28,
  });
}
