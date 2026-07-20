import React from "react";
import { Icon } from "../components/ui";
import { LineageCanvas } from "../components/lineage/LineageCanvas";
import { reviewService } from "../services/reviewService";

const EDGE_LABELS = {
  script_reads_table: "脚本读表",
  script_writes_table: "脚本写表",
  schedule_dependency: "调度依赖",
};

export function LineagePage({ taskId, selection, onBack }) {
  const [graph, setGraph] = React.useState(null);
  const [selectedId, setSelectedId] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");

  const loadGraph = React.useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await reviewService.getAuditTaskLineage(taskId, {
        rootKey: selection.lineageKey,
      });
      setGraph(data);
      setSelectedId(data.rootId);
    } catch (cause) {
      setError(cause.message || "血缘子图加载失败。");
    } finally {
      setLoading(false);
    }
  }, [selection.lineageKey, taskId]);

  React.useEffect(() => { void loadGraph(); }, [loadGraph]);

  const selected = graph?.nodes.find((node) => node.id === selectedId)
    || graph?.nodes.find((node) => node.id === graph?.rootId);
  const related = graph?.edges.filter((edge) => edge.sourceId === selected?.id || edge.targetId === selected?.id) || [];

  return <div className="lineage-page fade-in">
    <div className="lineage-page-head">
      <div>
        <button type="button" className="btn ghost sm" onClick={onBack}><Icon name="chevron" size={13} style={{ transform: "rotate(180deg)" }} /> 返回审查结果</button>
        <h1>Python 数据血缘</h1>
        <p className="muted mono">{selection.script} · {selection.job || "未关联作业"}</p>
      </div>
      <div className="lineage-filters">
        <button type="button" className="btn" onClick={loadGraph} disabled={loading}><Icon name="refresh" size={14} />{loading ? "加载中" : "刷新"}</button>
      </div>
    </div>
    {error ? <div className="card lineage-state" role="alert"><b>血缘加载失败</b><p>{error}</p><button className="btn" onClick={loadGraph}>重试</button></div> : null}
    {loading && !graph ? <div className="card lineage-state">正在加载当前脚本的直接读写链路…</div> : null}
    {graph ? <>
      {(graph.diagnostics || []).map((item) => <div className="lineage-notice" key={item.code}>{item.message}</div>)}
      <div className="lineage-layout">
        <section className="card lineage-graph-card" aria-busy={loading}>
          <div className="lineage-card-head"><span>{graph.nodes.length} 节点 / {graph.edges.length} 关系</span><span className="badge info">{graph.overlayRevision || "current"}</span></div>
          <LineageCanvas graph={graph} onSelect={setSelectedId} />
        </section>
        <aside className="card lineage-detail">
          <div className="lineage-card-head"><span>节点详情</span><span className="badge">{selected?.kind}</span></div>
          {selected ? <div className="lineage-detail-content">
            <h2>{selected.name}</h2><p>{selected.displayName}</p>
            <dl>
              <dt>类型</dt><dd>{selected.kind === "task" ? "Python / 调度任务" : "数据表"}</dd>
              <dt>程序路径</dt><dd className="mono">{selected.attributes?.programPath || "-"}</dd>
              <dt>结果表</dt><dd className="mono">{selected.attributes?.resultTable || "-"}</dd>
              <dt>状态</dt><dd>{selected.attributes?.disabled ? "禁用" : "启用"}</dd>
              <dt>数据来源</dt><dd>{selected.attributes?.source === "current_change" ? "本次修改" : "生产基线"}</dd>
            </dl>
            <h3>关系证据</h3>
            <div className="lineage-evidence-list">{related.map((edge) => <div className="lineage-evidence" key={edge.id}><b>{EDGE_LABELS[edge.kind] || edge.kind}</b><span>{edge.evidence.description}</span><small className="mono">{edge.evidence.sourceRecordId}</small></div>)}</div>
          </div> : null}
        </aside>
      </div>
    </> : null}
  </div>;
}
