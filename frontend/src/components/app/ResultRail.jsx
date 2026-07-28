import { useState } from "react";
import { getReportKey, reportAudit } from "../../utils/fineReportPresentation";
import { getScriptKey, scriptAudit } from "../../utils/scriptAuditPresentation";
import { Icon } from "../ui";

export function ResultRail({
  data,
  active,
  activeScriptKey,
  activeReportKey,
  onJump,
  onJumpScript,
  onJumpReport,
  collapsed,
  params,
  nav,
  mobileOpen,
}) {
  const [expandedBranches, setExpandedBranches] = useState(
    () => new Set(["python", "reports"]),
  );
  const pythonScripts = Array.isArray(data?.pyScripts) ? data.pyScripts : [];
  const fineReports = Array.isArray(data?.reports) ? data.reports : [];

  return (
    <aside
      className={`rail${collapsed ? " collapsed" : ""}${mobileOpen ? " mobile-open" : ""}`}
    >
      <div className="rail-head">
        <img className="brand-mark" src="/favicon.svg" alt="代码提交审查平台" />
        {!collapsed ? (
          <div style={{ minWidth: 0 }}>
            <div className="brand-name">代码提交审查平台</div>
            <div className="brand-sub">Code Review</div>
          </div>
        ) : null}
      </div>
      <div className="rail-scroll">
        <div className="rail-group-label">审查结果</div>
        {nav.map((section) => {
          if (section.id === "ai") return null;
          const rows = section.get ? section.get(data) : null;
          const tone =
            rows && !section.neutral
              ? rows.some((item) => item.level === "err")
                ? "err"
                : rows.some((item) => item.level === "warn")
                  ? "warn"
                  : "ok"
              : null;
          const count = rows ? rows.length : null;
          const isPython = section.id === "python";
          const isReports = section.id === "reports";
          const nestedItems = isPython
            ? pythonScripts
            : isReports
              ? fineReports
              : null;
          if (section.id !== "overview" && count === 0 && !nestedItems?.length)
            return null;
          if (nestedItems) {
            const isExpanded = expandedBranches.has(section.id);
            const directoryLabel = isPython
              ? "Python 脚本目录"
              : "FineReport 报表目录";
            return (
              <div key={section.id} className="nav-branch">
                <div
                  className={`navitem${active === section.id ? " active" : ""}`}
                  onClick={() => {
                    setExpandedBranches((current) =>
                      new Set(current).add(section.id),
                    );
                    onJump(section.id);
                  }}
                >
                  <span className="ni-ico">
                    <Icon name={section.icon} size={15} />
                  </span>
                  {!collapsed ? (
                    <span className="ni-label">{section.label}</span>
                  ) : null}
                  {!collapsed && count != null ? (
                    <span className={`ni-count${tone ? ` ${tone}` : ""}`}>
                      {count}
                    </span>
                  ) : null}
                  {!collapsed ? (
                    <button
                      type="button"
                      className={`nav-branch-toggle${isExpanded ? " open" : ""}`}
                      aria-label={`${isExpanded ? "收起" : "展开"}${directoryLabel}`}
                      aria-expanded={isExpanded}
                      onClick={(event) => {
                        event.stopPropagation();
                        setExpandedBranches((current) => {
                          const next = new Set(current);
                          if (next.has(section.id)) next.delete(section.id);
                          else next.add(section.id);
                          return next;
                        });
                      }}
                    >
                      <Icon name="chevron" size={13} />
                    </button>
                  ) : null}
                </div>
                {!collapsed && isExpanded ? (
                  <div
                    className="nav-children"
                    role="group"
                    aria-label={directoryLabel}
                  >
                    {nestedItems.map((item) => {
                      const itemKey = isPython
                        ? getScriptKey(item)
                        : getReportKey(item);
                      const itemLevel = isPython
                        ? scriptAudit(item).level
                        : reportAudit(item).level;
                      const itemLabel = isPython
                        ? item.script
                        : item.title || item.file;
                      const itemTitle = isPython
                        ? item.script
                        : `${item.title || item.file} · ${item.file}`;
                      const isActive = isPython
                        ? activeScriptKey === itemKey
                        : activeReportKey === itemKey;
                      return (
                        <button
                          type="button"
                          key={itemKey}
                          className={`nav-child${isActive ? " active" : ""}`}
                          title={itemTitle}
                          onClick={() =>
                            isPython ? onJumpScript(item) : onJumpReport(item)
                          }
                        >
                          <span
                            className={`nav-child-status ${itemLevel}`}
                            aria-label={itemLevel}
                          />
                          <span className="nav-child-label mono">
                            {itemLabel}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            );
          }
          return (
            <div
              key={section.id}
              className={`navitem${active === section.id ? " active" : ""}`}
              onClick={() => onJump(section.id)}
            >
              <span className="ni-ico">
                <Icon name={section.icon} size={15} />
              </span>
              {!collapsed ? (
                <span className="ni-label">{section.label}</span>
              ) : null}
              {!collapsed && count != null ? (
                <span className={`ni-count${tone ? ` ${tone}` : ""}`}>
                  {count}
                </span>
              ) : null}
            </div>
          );
        })}
        {params.ai ? (
          <div
            className={`navitem${active === "ai" ? " active" : ""}`}
            onClick={() => onJump("ai")}
          >
            <span className="ni-ico" style={{ color: "var(--accent)" }}>
              <Icon name="sparkle" size={15} />
            </span>
            {!collapsed ? <span className="ni-label">AI 分析</span> : null}
          </div>
        ) : null}
      </div>
    </aside>
  );
}
