export function getRootNeighborhoodNodeIds(graph) {
  if (!graph?.rootId) return [];
  const ids = new Set([graph.rootId]);
  for (const edge of graph.edges || []) {
    if (edge.sourceId === graph.rootId) ids.add(edge.targetId);
    if (edge.targetId === graph.rootId) ids.add(edge.sourceId);
  }
  return [...ids];
}
