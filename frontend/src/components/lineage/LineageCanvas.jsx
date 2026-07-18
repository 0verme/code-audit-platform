import React from "react";
import "../../vendor/lineage-viewer/define.js";
import { toViewerGraph } from "./lineageAdapter.js";
import { getRootNeighborhoodNodeIds } from "./lineageViewport.js";

const ROOT_FIT = { padding: 48, maxScale: 1 };

export const LineageCanvas = React.forwardRef(function LineageCanvas({
  graph,
  onSelect,
  ariaLabel = "Python 上下游血缘图",
  compact = false,
  focusLabel = "定位根节点",
  showRootControl = true,
  showSelfLoops = false,
}, ref) {
  const hostRef = React.useRef(null);
  const viewerRef = React.useRef(null);

  React.useImperativeHandle(ref, () => ({
    zoomIn: () => viewerRef.current?.zoomBy(1.2),
    zoomOut: () => viewerRef.current?.zoomBy(1 / 1.2),
    fitView: () => viewerRef.current?.fitView(),
    focusRoot: () => viewerRef.current?.fitNodes(getRootNeighborhoodNodeIds(graph), ROOT_FIT),
  }), [graph]);

  React.useEffect(() => {
    const host = hostRef.current;
    if (!host || !graph) return undefined;
    const viewer = document.createElement("lineage-viewer");
    const handleClick = (event) => onSelect?.(event.detail.nodeId);
    const focusRoot = () => viewer.fitNodes(getRootNeighborhoodNodeIds(graph), ROOT_FIT);
    viewer.options = {
      direction: "LR", fitOnLoad: false, nodeWidth: 220, nodeHeight: 72,
      highlightMode: "connected", validationMode: "strict", showSelfLoops,
    };
    viewer.data = toViewerGraph(graph);
    viewer.addEventListener("lineage-node-click", handleClick);
    viewer.addEventListener("lineage-ready", focusRoot, { once: true });
    host.replaceChildren(viewer);
    viewerRef.current = viewer;
    return () => {
      viewerRef.current = null;
      viewer.removeEventListener("lineage-node-click", handleClick);
      viewer.removeEventListener("lineage-ready", focusRoot);
      viewer.destroy?.();
    };
  }, [graph, onSelect, showSelfLoops]);

  return <div className="lineage-canvas-shell">
    <div className="lineage-view-tools" role="group" aria-label="血缘图视图操作">
      <button type="button" className="btn ghost sm" onClick={() => viewerRef.current?.zoomBy(1 / 1.2)} aria-label="缩小">−</button>
      <button type="button" className="btn ghost sm" onClick={() => viewerRef.current?.zoomBy(1.2)} aria-label="放大">+</button>
      {showRootControl ? <button type="button" className="btn ghost sm" onClick={() => viewerRef.current?.fitNodes(getRootNeighborhoodNodeIds(graph), ROOT_FIT)}>{focusLabel}</button> : null}
      <button type="button" className="btn ghost sm" onClick={() => viewerRef.current?.fitView()}>适应画布</button>
    </div>
    <div className={`lineage-canvas${compact ? " lineage-canvas-compact" : ""}`} ref={hostRef} aria-label={ariaLabel} />
  </div>;
});
