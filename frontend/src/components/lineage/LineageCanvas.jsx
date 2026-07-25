import React from "react";
import { getRootNeighborhoodNodeIds } from "@lineage-viewer/domain-adapter";
import { LineageViewerCanvas } from "@lineage-viewer/react";

import { toViewerGraph } from "./lineageAdapter.js";

const ROOT_FIT = { padding: 48, maxScale: 1 };

export const LineageCanvas = React.forwardRef(function LineageCanvas({
  graph,
  onSelect,
  ariaLabel = "数据血缘图",
  compact = false,
  focusLabel = "定位根节点",
  initialFit = "root",
  showRootControl = true,
  showSelfLoops = false,
}, ref) {
  const viewerRef = React.useRef(null);
  const viewerGraph = React.useMemo(() => toViewerGraph(graph), [graph]);
  const rootNodeIds = React.useMemo(() => getRootNeighborhoodNodeIds(graph), [graph]);
  const viewerOptions = React.useMemo(() => ({
    direction: "LR",
    fitOnLoad: false,
    nodeWidth: 220,
    nodeHeight: 72,
    highlightMode: "connected",
    validationMode: "strict",
    showSelfLoops,
  }), [showSelfLoops]);

  React.useImperativeHandle(ref, () => ({
    zoomIn: () => viewerRef.current?.zoomBy(1.2),
    zoomOut: () => viewerRef.current?.zoomBy(1 / 1.2),
    fitView: () => viewerRef.current?.fitView(),
    focusRoot: () => viewerRef.current?.fitNodes(rootNodeIds, ROOT_FIT),
  }), [rootNodeIds]);

  return <div className="lineage-canvas-shell">
    <div className="lineage-view-tools" role="group" aria-label="血缘图视图操作">
      <button type="button" className="btn ghost sm" onClick={() => viewerRef.current?.zoomBy(1 / 1.2)} aria-label="缩小">−</button>
      <button type="button" className="btn ghost sm" onClick={() => viewerRef.current?.zoomBy(1.2)} aria-label="放大">+</button>
      {showRootControl ? <button type="button" className="btn ghost sm" onClick={() => viewerRef.current?.fitNodes(rootNodeIds, ROOT_FIT)}>{focusLabel}</button> : null}
      <button type="button" className="btn ghost sm" onClick={() => viewerRef.current?.fitView()}>适应画布</button>
    </div>
    <LineageViewerCanvas
      ref={viewerRef}
      className={`lineage-canvas${compact ? " lineage-canvas-compact" : ""}`}
      aria-label={ariaLabel}
      data={viewerGraph}
      options={viewerOptions}
      initialFit={initialFit === "view" ? "view" : rootNodeIds}
      initialFitOptions={ROOT_FIT}
      onNodeSelect={({ nodeId }) => onSelect?.(nodeId)}
    />
  </div>;
});
