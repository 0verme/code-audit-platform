const shorten = (value, maxLength = 28) => {
  const text = String(value || "");
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
};

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
  return {
    schemaVersion: "1.0",
    nodes: graph.nodes.map((node) => ({
      id: node.id,
      label: shorten(node.name),
      subtitle: shorten(node.displayName),
      type: node.kind === "task" ? "job" : "table",
      layer: node.namespace,
      ...(node.status ? { status: node.status } : {}),
      metadata: { kind: node.kind, fullLabel: node.name, fullSubtitle: node.displayName },
    })),
    edges: graph.edges.map((edge) => ({
      id: edge.id,
      source: edge.sourceId,
      target: edge.targetId,
      label: edge.kind.replaceAll("_", " "),
      type: edge.kind === "schedule_dependency" ? "dependency" : "lineage",
    })),
  };
}
