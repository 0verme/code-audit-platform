import { useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "../components/ui";
import { reviewService } from "../services/reviewService";


const STATUS = {
  pending: { label: "待审核", tone: "pending" },
  passed: { label: "等待上线", tone: "passed" },
  completed: { label: "处理完成", tone: "completed" },
  reviewing: { label: "审核中", tone: "reviewing" },
  rejected: { label: "已驳回", tone: "rejected" },
  launched: { label: "已上线", tone: "launched" },
  processing: { label: "处理中", tone: "processing" },
  unknown: { label: "未知状态", tone: "unknown" },
};

const REQUIREMENT_TYPES = ["开发维护", "运行维护", "数据修改"];

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
  const [selectedTypes, setSelectedTypes] = useState(() => new Set(REQUIREMENT_TYPES));
  const [refreshKey, setRefreshKey] = useState(0);
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const [exportState, setExportState] = useState({ loading: false, error: null });
  const selectAllTypesRef = useRef(null);
  const allTypesSelected = selectedTypes.size === REQUIREMENT_TYPES.length;

  useEffect(() => {
    if (selectAllTypesRef.current) {
      selectAllTypesRef.current.indeterminate = selectedTypes.size > 0 && !allTypesSelected;
    }
  }, [allTypesSelected, selectedTypes]);

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
    return items.filter((item) => (
      (status === "all" || item.status === status) && selectedTypes.has(item.type)
    ));
  }, [selectedTypes, state.data?.items, status]);
  const summary = state.data?.summary || {};

  const toggleAllTypes = () => {
    setSelectedTypes(allTypesSelected ? new Set() : new Set(REQUIREMENT_TYPES));
  };

  const toggleType = (type) => {
    setSelectedTypes((current) => {
      const next = new Set(current);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const exportXlsx = async () => {
    setExportState({ loading: true, error: null });
    try {
      const types = REQUIREMENT_TYPES.filter((type) => selectedTypes.has(type));
      const { blob, filename } = await reviewService.exportPublishList(selectedDate, { status, types });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setExportState({ loading: false, error: null });
    } catch (error) {
      setExportState({ loading: false, error });
    }
  };

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
          <button
            type="button"
            className="pl-button"
            disabled={state.loading || Boolean(state.error) || selectedTypes.size === 0 || exportState.loading}
            onClick={exportXlsx}
          >
            <Icon name="download" size={15} /> {exportState.loading ? "导出中" : "导出 XLSX"}
          </button>
          <button type="button" className="pl-button primary" disabled={state.loading} onClick={() => setRefreshKey((key) => key + 1)}>
            <Icon name="refresh" size={15} /> {state.loading ? "加载中" : "刷新"}
          </button>
        </div>
      </header>

      {exportState.error ? (
        <div className="publish-list-export-error" role="alert">
          XLSX 导出失败：{exportState.error.message || "请稍后重试。"}
        </div>
      ) : null}

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
            {["all", "launched", "passed", "completed", "reviewing", "processing"].map((key) => (
              <button key={key} type="button" className={status === key ? "active" : ""} onClick={() => setStatus(key)}>
                {key === "all" ? "全部" : STATUS[key].label}
              </button>
            ))}
          </div>
        </div>
        <div className="publish-list-type-filter" role="group" aria-label="按需求类型筛选">
          <span>需求类型</span>
          <label>
            <input
              ref={selectAllTypesRef}
              type="checkbox"
              checked={allTypesSelected}
              onChange={toggleAllTypes}
            />
            全选
          </label>
          {REQUIREMENT_TYPES.map((type) => (
            <label key={type}>
              <input
                type="checkbox"
                checked={selectedTypes.has(type)}
                onChange={() => toggleType(type)}
              />
              {type}
            </label>
          ))}
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
          <span>共 {visibleItems.length} 条{status !== "all" || !allTypesSelected ? "（已筛选）" : ""}{state.data?.truncated ? "，仅展示前 1000 条" : ""}</span>
        </footer>
      </section>
    </main>
  );
}
