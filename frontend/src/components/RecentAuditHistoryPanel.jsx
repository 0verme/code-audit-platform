import { useEffect, useMemo, useState } from "react";
import { AUDIT_WORKFLOWS } from "../config/auditWorkflows";
import { auditSourceDisplayRules } from "../config/auditSourceDisplayConfig";
import { Dot, Icon } from "./ui";
import {
  formatRecentAuditTime,
  getRecentAuditPagination,
  getRecentAuditSubtitle,
  RECENT_AUDIT_PAGE_SIZE,
} from "./recentAuditHistory";
import { formatAuditSourceDisplay } from "../utils/auditSourceDisplay";

function RecentAuditPagination({ currentPage, totalPages, totalItems, onPageChange }) {
  return (
    <div className="recent-pagination" aria-label="最近审查分页">
      <span className="recent-pagination-summary">
        共 {totalItems} 条，第 {currentPage} / {totalPages} 页
      </span>
      <div className="recent-pagination-actions">
        <button
          type="button"
          className="btn ghost sm"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
        >
          上一页
        </button>
        <button
          type="button"
          className="btn ghost sm"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
        >
          下一页
        </button>
      </div>
    </div>
  );
}

export function RecentAuditHistoryPanel({
  items,
  loading,
  error,
  onSelect,
  defaultOpen = false,
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [currentPage, setCurrentPage] = useState(1);

  const pagination = useMemo(
    () => getRecentAuditPagination(items, currentPage, RECENT_AUDIT_PAGE_SIZE),
    [items, currentPage],
  );

  useEffect(() => {
    if (pagination.currentPage !== currentPage) {
      setCurrentPage(pagination.currentPage);
    }
  }, [currentPage, pagination.currentPage]);

  return (
    <section className={`recent-history-panel${open ? " open" : ""}`}>
      <button
        type="button"
        className="recent-history-trigger"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
      >
        <span className="recent-history-icon">
          <Icon name="clock" size={16} />
        </span>
        <span className="recent-history-copy">
          <span className="recent-history-title">最近审查</span>
          <span className="recent-history-subtitle">
            {getRecentAuditSubtitle(items.length, RECENT_AUDIT_PAGE_SIZE)}
          </span>
        </span>
        <span className="recent-history-meta">
          <Icon
            name="chevron"
            size={16}
            className="recent-history-chevron"
          />
        </span>
      </button>

      {open ? (
        <div className="recent-history-body">
          {loading ? (
            <div className="card recent-list">正在加载任务列表...</div>
          ) : (
            <div className="card recent-list">
              {pagination.totalItems ? (
                <>
                  <div className="recent-table-wrap">
                    <div className="recent-head recent-audits-row">
                      <span className="recent-audits-status-cell">状态</span>
                      <span className="recent-audits-source-cell">审查来源</span>
                      <span className="recent-audits-type-cell">审查类型</span>
                      <span className="recent-audits-ip-cell">IP</span>
                      <span className="recent-audits-time-cell">时间</span>
                    </div>
                    {pagination.pagedItems.map((item, index) => {
                      const workflow =
                        AUDIT_WORKFLOWS.find((entry) => entry.id === item.wf) ||
                        AUDIT_WORKFLOWS[0];
                      const sourceDisplay = formatAuditSourceDisplay(
                        item.sourceRef,
                        item.sourceType,
                        auditSourceDisplayRules,
                      );
                      const tone =
                        item.status === "pass"
                          ? "ok"
                          : item.status === "fail"
                            ? "err"
                            : "warn";
                      return (
                        <div
                          key={`${item.id ?? item.rev}-${index}`}
                          className="recent-row"
                          onClick={() => onSelect(item)}
                        >
                          <span className="rr-status" aria-label={`审查状态：${item.status || "unknown"}`}>
                            <Dot tone={tone} />
                          </span>
                          <span className="rr-source recent-audits-source-cell">
                            <span className="rr-tag">{item.sourceTag}</span>
                            <span
                              className="rr-source-text recent-audits-source-path mono"
                              title={sourceDisplay.fullText}
                            >
                              {sourceDisplay.displayText}
                            </span>
                          </span>
                          <span
                            className="rr-wf recent-audits-type-cell"
                            title={workflow.name}
                          >
                            <Icon
                              name={workflow.icon}
                              size={12}
                              style={{ color: workflow.color }}
                            />{" "}
                            {workflow.shortName}
                          </span>
                          <span className="rr-who recent-audits-ip-cell">{item.who}</span>
                          <span className="rr-when recent-audits-time-cell">
                            {formatRecentAuditTime(item.when)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                  {pagination.hasPagination ? (
                    <RecentAuditPagination
                      currentPage={pagination.currentPage}
                      totalPages={pagination.totalPages}
                      totalItems={pagination.totalItems}
                      onPageChange={setCurrentPage}
                    />
                  ) : null}
                </>
              ) : (
                <div className="recent-empty">暂无最近审查记录</div>
              )}
            </div>
          )}
          {error ? (
            <p className="route-hint" style={{ color: "var(--err)" }}>
              任务接口不可用，无法加载真实任务列表。
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
