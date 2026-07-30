import { useEffect, useMemo, useState } from "react";
import { Icon } from "../components/ui";
import { reviewService } from "../services/reviewService";


const STATUS = {
  pending: { label: "待审核", tone: "pending" },
  passed: { label: "等待上线", tone: "passed" },
  completed: { label: "处理完成", tone: "passed" },
  reviewing: { label: "审核中", tone: "reviewing" },
  rejected: { label: "已驳回", tone: "rejected" },
  launched: { label: "已上线", tone: "launched" },
  processing: { label: "处理中", tone: "reviewing" },
  unknown: { label: "未知状态", tone: "unknown" },
};

function localDateString(value = new Date()) {
  const offset = value.getTimezoneOffset() * 60_000;
  return new Date(value.getTime() - offset).toISOString().slice(0, 10);
}

function ownerInitial(name) {
  return (name || "?").trim().slice(0, 1).toUpperCase();
}

export default function PublishListPage() {
  const [selectedDate, setSelectedDate] = useState(localDateString);
  const [status, setStatus] = useState("all");
  const [refreshKey, setRefreshKey] = useState(0);
  const [state, setState] = useState({ data: null, loading: true, error: null });

  useEffect(() => {
    let cancelled = false;
    setState((current) => ({ ...current, loading: true, error: null }));
    reviewService.getPublishList(selectedDate)
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((error) => {
        if (!cancelled) setState({ data: null, loading: false, error });
      });
    return () => { cancelled = true; };
  }, [selectedDate, refreshKey]);

  const visibleItems = useMemo(() => {
    const items = state.data?.items || [];
    return status === "all" ? items : items.filter((item) => item.status === status);
  }, [state.data?.items, status]);
  const summary = state.data?.summary || {};

  return (
    <main className="publish-list-page">
      <header className="publish-list-header">
        <div>
          <div className="publish-list-kicker"><span /> 代码提交审查平台 · 上线清单</div>
          <h1>当日上线清单</h1>
          <p>汇总选定日期计划上线的应用与服务，便于值班与发布核对。</p>
        </div>
        <div className="publish-list-actions">
          <label className="publish-list-date">
            <span>上线日期</span>
            <input type="date" value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} />
          </label>
          <button type="button" className="pl-button" onClick={() => setSelectedDate(localDateString())}>
            <Icon name="calendar" size={15} /> 今天
          </button>
          <button type="button" className="pl-button primary" disabled={state.loading} onClick={() => setRefreshKey((key) => key + 1)}>
            <Icon name="refresh" size={15} /> {state.loading ? "加载中" : "刷新"}
          </button>
        </div>
      </header>

      <section className="publish-list-stats" aria-label="上线概览">
        <div><span>计划上线</span><strong>{summary.total || 0}<small>项</small></strong></div>
        <div><span>等待上线 / 处理完成</span><strong>{(summary.passed || 0) + (summary.completed || 0)}<small>项</small></strong></div>
        <div><span>审核中</span><strong>{summary.reviewing || 0}<small>项</small></strong></div>
        <div><span>处理中</span><strong>{summary.processing || 0}<small>项</small></strong></div>
      </section>

      <section className="publish-list-card">
        <div className="publish-list-toolbar">
          <div className="publish-list-card-title">
            <span className="publish-list-card-icon"><Icon name="list" size={17} /></span>
            <div><strong>上线明细</strong><small>计划上线 {summary.total || 0} 项 · 日期 {selectedDate}</small></div>
          </div>
          <div className="publish-list-filters" role="group" aria-label="按审核状态筛选">
            {["all", "passed", "completed", "reviewing", "processing", "launched"].map((key) => (
              <button key={key} type="button" className={status === key ? "active" : ""} onClick={() => setStatus(key)}>
                {key === "all" ? "全部" : STATUS[key].label}
              </button>
            ))}
          </div>
        </div>

        {state.error ? (
          <div className="publish-list-message error"><Icon name="x" size={20} /><strong>上线清单加载失败</strong><span>{state.error.message || "请检查后端服务与数据库字段映射。"}</span></div>
        ) : state.loading && !state.data ? (
          <div className="publish-list-message"><Icon name="clock" size={20} /><strong>正在加载上线清单…</strong></div>
        ) : visibleItems.length === 0 ? (
          <div className="publish-list-message"><Icon name="calendar" size={22} /><strong>该日期暂无匹配的上线计划</strong><span>可切换日期或状态筛选后重试。</span></div>
        ) : (
          <div className="publish-list-table-wrap">
            <table>
              <thead><tr><th>需求 ID</th><th>需求类型</th><th>开发人员</th><th>需求标题</th><th>状态</th><th>计划发布日期</th><th>来源</th><th>详情</th></tr></thead>
              <tbody>
                {visibleItems.map((item, index) => {
                  const statusMeta = STATUS[item.status] || STATUS.unknown;
                  return (
                    <tr key={`${item.id}-${index}`}>
                      <td>
                        {item.detailUrl ? (
                          <a className="publish-list-id" href={item.detailUrl} target="_blank" rel="noreferrer">{item.id || "-"}</a>
                        ) : <span className="publish-list-id">{item.id || "-"}</span>}
                      </td>
                      <td>{item.type || "-"}</td>
                      <td><span className="publish-list-owner"><i>{ownerInitial(item.owner)}</i>{item.owner || "-"}</span></td>
                      <td><strong className="publish-list-title">{item.title || "-"}</strong></td>
                      <td><span className={`publish-list-badge ${statusMeta.tone}`}>{item.statusLabel || statusMeta.label}</span></td>
                      <td>{item.date || selectedDate}{item.time ? ` ${item.time}` : ""}</td>
                      <td>{item.source || "-"}</td>
                      <td>
                        {item.detailUrl ? <a className="publish-list-link" href={item.detailUrl} target="_blank" rel="noreferrer">查看</a> : item.remark ? (
                          <details className="publish-list-detail"><summary>查看</summary><div>{item.remark}</div></details>
                        ) : <span className="muted">-</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <footer className="publish-list-card-footer">
          <span>共 {visibleItems.length} 条{status !== "all" ? "（已筛选）" : ""}{state.data?.truncated ? "，仅展示前 1000 条" : ""}</span>
        </footer>
      </section>
    </main>
  );
}
