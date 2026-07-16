const shorten = (value, maxLength = 28) => {
  const text = String(value || "");
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
};

export function toViewerGraph(graph) {
  return {
    schemaVersion: "1.0",
    nodes: graph.nodes.map((node) => ({
      id: node.id,
      label: shorten(node.name),
      subtitle: shorten(node.displayName),
      type: node.kind === "task" ? "job" : "table",
      layer: node.namespace,
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
