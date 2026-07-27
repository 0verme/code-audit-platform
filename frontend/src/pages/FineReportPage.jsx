import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Badge, Icon, Metric, OkState, Panel, Sev } from "../components/ui";
import { ReferenceTableList } from "../components/ReferenceTableList";
import { SourceFileLinks } from "../components/SourceFileLinks";
import { AiSection, AssetIssuesSection, STATUS_META } from "./ResultsPage";
import { shouldDefaultOpenChangeList } from "../utils/changeListPresentation";
import { sortAlertRows } from "../utils/alertSorting";
import {
  FINE_REPORT_REF_TABLE_GROUPS,
  groupFineReportRefTables,
  syncAutoOpenReportIds,
} from "../utils/fineReportPresentation";
import { countSqlLines } from "../utils/sqlPresentation";

const FR_CAT = {
  dataset: { label: "数据集", icon: "db" },
  conn: { label: "连接", icon: "link" },
  param: { label: "参数", icon: "layers" },
  tpl: { label: "模板", icon: "grid" },
  perf: { label: "性能", icon: "gauge" },
  perm: { label: "权限", icon: "shield" },
};

export const FR_NAV = [
  { id: "overview", label: "概览", icon: "layers" },
  { id: "changes", label: "变更文件", icon: "git", get: (data) => data.changes, neutral: true },
  { id: "menu", label: "目录", icon: "folder", get: (data) => data.menu?.rows, neutral: true },
  { id: "authority", label: "权限", icon: "shield", get: (data) => data.authority?.rows, neutral: true },
  { id: "reports", label: "报表检查", icon: "grid", get: (data) => data.reports, neutral: true },
];

function reportAudit(report) {
  const issues = report.issues || [];
  const err = issues.filter((item) => item.level === "err").length;
  const warn = issues.filter((item) => item.level === "warn").length;
  return { err, warn, total: issues.length, level: err ? "err" : warn ? "warn" : "ok" };
}

function reportType(report) {
  return report.type === "frm"
    ? { icon: "screen", label: "决策大屏 .frm" }
    : { icon: "grid", label: "普通报表 .cpt" };
}

function FrStatusHeader({ d }) {
  const task = d.task;
  const status = STATUS_META[task.status] || STATUS_META.warn;
  const reports = Array.isArray(d.reports) ? d.reports : [];
  const highRisk = reports.filter((report) => reportAudit(report).err).length;
  return (
    <div className={`status-hero card ${status.tone}`}>
      <div className="sh-main">
        <div className={`sh-badge ${status.tone}`}>
          <Icon name={status.icon} size={26} stroke={2.4} />
        </div>
        <div className="sh-text">
          <div className="sh-title-row">
            <h2 className="sh-title">{status.label}</h2>
            <Badge tone="accent" icon="grid">{task.workflow}</Badge>
          </div>
          <p className="sh-desc">
            {task.status === "pass"
              ? "所有报表均已通过检查，可以发布。"
              : "存在尚未解决的数据集、连接或权限问题。"}
          </p>
          <div className="sh-meta mono">
            <span><Icon name="branch" size={12} /> {task.revision}</span>
            <span className="sh-sep">/</span>
            <span>{task.author}</span>
            <span className="sh-sep">/</span>
            <span><Icon name="clock" size={12} /> {task.startedAt}</span>
            <span className="sh-sep">/</span>
            <span>时长 {task.duration}</span>
          </div>
        </div>
      </div>
      <div className="metrics sh-metrics">
        <Metric label="报表" value={task.reports} icon="grid" />
        <Metric label="检查项" value={task.checks} icon="layers" />
        <Metric label="错误" value={task.errors} tone={task.errors ? "err" : "ok"} icon="x" />
        <Metric label="警告" value={task.warnings} tone={task.warnings ? "warn" : "ok"} icon="alert" />
        <Metric label="高风险" value={highRisk} tone={highRisk ? "err" : "ok"} icon="shield" />
      </div>
    </div>
  );
}

function ReportListSection({ d, reg, openReportIds, onToggle, loading = false }) {
  const reports = d.reports || [];
  const flagged = reports.filter((report) => reportAudit(report).total).length;
  const anyErr = reports.some((report) => reportAudit(report).err);

  return (
    <Panel
      id="reports"
      icon="grid"
      title="报表检查列表"
      registerRef={reg}
      sub="数据集 / 连接 / 参数 / 模板 / 性能 / 权限"
      count={flagged ? `${flagged} 个报表需要修复` : "全部通过"}
      countTone={flagged ? (anyErr ? "err" : "warn") : "ok"}
    >
      <div className="panel-body flush">
        <div className="pas-list">
          {loading ? (
            <div className="empty-state">正在生成报表检查明细，请稍候…</div>
          ) : null}
          {!loading && !reports.length ? (
            <div className="empty-state">本次审查未发现可展示的报表检查项。</div>
          ) : null}
          {!loading && reports.map((report) => {
            const audit = reportAudit(report);
            const type = reportType(report);
            const detailId = `report-detail-${encodeURIComponent(report.file)}`;
            const isOpen = openReportIds.has(report.file);
            return (
              <div key={report.file} className={`accordion-item${isOpen ? " open" : ""}`}>
                <button className="fr-row" onClick={() => onToggle(report.file)} aria-expanded={isOpen} aria-controls={detailId}>
                <span className={`fr-ico ${report.type}`}>
                  <Icon name={type.icon} size={16} />
                </span>
                <span className="pas-main">
                  <span className="fr-name">
                    <span className={`chg-tag ${report.change}`}>{report.change}</span>
                    {report.title}
                  </span>
                  <span className="pas-sub mono">{report.file}</span>
                </span>
                <span className="fr-meta mono">
                  <span className="fr-type">{report.type === "frm" ? "FRM" : "CPT"}</span>
                  <span className="fr-dot">/</span>
                  <span>数据集 {report.datasets.length}</span>
                  <span className="fr-dot">/</span>
                  <span>引用表 {Array.isArray(report.refTables) ? report.refTables.length : 0}</span>
                </span>
                <span className="pas-tags">
                  <span className="pas-grp-label">检查</span>
                  {audit.err ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{audit.err}</span> : null}
                  {audit.warn ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{audit.warn}</span> : null}
                  {!audit.total ? <span className="sev ok"><Icon name="check" size={11} stroke={2.4} />通过</span> : null}
                </span>
                <Icon name="chevron" size={16} className="pas-chev" />
                </button>
                <ReportDetailAccordion report={report} detailId={detailId} open={isOpen} onClose={() => onToggle(report.file)} />
              </div>
            );
          })}
        </div>
      </div>
    </Panel>
  );
}

function FineChangesSection({ d, reg }) {
  const changes = Array.isArray(d.changes) ? d.changes : [];
  if (!changes.length) return null;
  return (
    <Panel
      id="changes"
      icon="git"
      title="变更文件列表"
      registerRef={reg}
      count={changes.length}
      countTone="info"
      defaultOpen={shouldDefaultOpenChangeList(changes.length)}
    >
      <div className="panel-body flush">
        <div className="flist">
          {changes.map((change) => (
            <div key={change.path} className="frow">
              <span className={`chg-tag ${change.type}`}>{change.type}</span>
              <span className="fpath">{change.path}</span>
              <Badge>{change.cat}</Badge>
              {change.downloadUrl ? (
                <a className="dl-link" href={change.downloadUrl} target="_blank" rel="noreferrer">
                  <Icon name="download" size={12} /> 下载
                </a>
              ) : null}
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}

function TxtTableSection({ id, icon, title, section, reg }) {
  if (!section) return null;
  const messages = section.messages || [];
  const sortedMessages = sortAlertRows(messages);
  const severity = messages.some((m) => m.level === "err") ? "err" : messages.some((m) => m.level === "warn") ? "warn" : "ok";
  return (
    <Panel
      id={id}
      icon={icon}
      title={title}
      registerRef={reg}
      count={messages.length || "通过"}
      countTone={severity}
      defaultOpen={messages.length > 0}
    >
      <SourceFileLinks
        files={section.downloadUrl ? [{
          kind: id,
          path: section.file,
          name: section.file,
          downloadUrl: section.downloadUrl,
        }] : []}
      />
      <div className="panel-body">
        {section.rows?.length ? (
          <div className="table-wrap" style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden", marginBottom: messages.length ? 12 : 0 }}>
            <table className="tbl">
              <thead><tr>{section.columns.map((col) => <th key={col}>{col}</th>)}</tr></thead>
              <tbody>
                {section.rows.map((row, rowIndex) => (
                  <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={cellIndex} className="mono" style={{ fontSize: "var(--fs-xs)" }}>{cell}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        {messages.length ? (
          <div className="table-wrap" style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th style={{ width: 80 }}>级别</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                {sortedMessages.map((msg, index) => (
                  <tr key={index} className={msg.level === "err" ? "err-row" : msg.level === "warn" ? "warn-row" : ""}>
                    <td className="severity-cell"><Sev level={msg.level} /></td>
                    <td>{msg.msg}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <OkState>校验通过</OkState>}
      </div>
    </Panel>
  );
}

function DatasetSqlCard({ dataset, index }) {
  const [viewerOpen, setViewerOpen] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState("");
  const dialogRef = useRef(null);
  const triggerRef = useRef(null);
  const copyButtonRef = useRef(null);
  const copyTimerRef = useRef(null);
  const id = useId();
  const datasetName = dataset?.name || `未命名数据集 ${index + 1}`;
  const sql = typeof dataset?.sql === "string" ? dataset.sql : "";
  const sqlLineCount = countSqlLines(sql);
  const titleId = `fr-sql-title-${id}`;
  const descriptionId = `fr-sql-description-${id}`;

  const clearCopyTimer = () => {
    if (copyTimerRef.current) {
      window.clearTimeout(copyTimerRef.current);
      copyTimerRef.current = null;
    }
  };

  useEffect(() => () => clearCopyTimer(), []);

  useEffect(() => {
    if (!viewerOpen || !dialogRef.current) return;
    if (!dialogRef.current.open) dialogRef.current.showModal();
    copyButtonRef.current?.focus({ preventScroll: true });
  }, [viewerOpen]);

  const openViewer = () => {
    clearCopyTimer();
    setCopyFeedback("");
    setViewerOpen(true);
  };

  const closeViewer = () => {
    dialogRef.current?.close();
  };

  const handleDialogClose = () => {
    clearCopyTimer();
    setCopyFeedback("");
    setViewerOpen(false);
    triggerRef.current?.focus({ preventScroll: true });
  };

  const handleDialogKeyDown = (event) => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    event.stopPropagation();
    closeViewer();
  };

  const handleCopy = async () => {
    clearCopyTimer();
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard API unavailable");
      await navigator.clipboard.writeText(sql);
      setCopyFeedback("已复制");
      copyTimerRef.current = window.setTimeout(() => {
        setCopyFeedback("");
        copyTimerRef.current = null;
      }, 1600);
    } catch {
      setCopyFeedback("复制失败，请手动选择 SQL 复制");
    }
  };

  return (
    <>
      <div className="fr-ds">
        <div className="fr-ds-top">
          <span className="fr-ds-heading">
            <Icon name="db" size={14} />
            <span className="fr-ds-name mono">{datasetName}</span>
          </span>
          <span className="fr-ds-summary">
            <span className="fr-ds-rows mono">SQL {sqlLineCount} 行</span>
            {dataset?.rows !== null && dataset?.rows !== undefined && dataset?.rows !== ""
              ? <span className="fr-ds-rows mono">结果约 {dataset.rows} 行</span>
              : null}
            <button ref={triggerRef} type="button" className="btn sm" onClick={openViewer}>
              查看完整 SQL
            </button>
          </span>
        </div>
      </div>
      {viewerOpen ? (
        <dialog
          ref={dialogRef}
          className="fr-sql-viewer"
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          aria-describedby={descriptionId}
          onClose={handleDialogClose}
          onCancel={(event) => {
            event.preventDefault();
            event.stopPropagation();
            closeViewer();
          }}
          onKeyDown={handleDialogKeyDown}
        >
          <header className="fr-sql-viewer-toolbar">
            <div className="fr-sql-viewer-heading">
              <h2 id={titleId} className="fr-sql-viewer-title">{datasetName}</h2>
              <span id={descriptionId} className="fr-sql-viewer-meta mono">SQL {sqlLineCount} 行</span>
            </div>
            <div className="fr-sql-viewer-actions">
              <span className="fr-sql-copy-status" role="status" aria-live="polite">
                {copyFeedback}
              </span>
              <button
                ref={copyButtonRef}
                type="button"
                className="btn sm"
                onClick={handleCopy}
                title={`复制当前数据集 ${datasetName} 的完整 SQL`}
                aria-label={`复制当前数据集 ${datasetName} 的完整 SQL`}
              >
                <Icon name="copy" size={13} />
                {copyFeedback === "已复制" ? "已复制" : "复制 SQL"}
              </button>
              <button type="button" className="btn sm" onClick={closeViewer} aria-label="关闭 SQL 查看器">
                <Icon name="x" size={13} />
                关闭
              </button>
            </div>
          </header>
          <pre className="fr-sql-viewer-content mono" tabIndex={0}>{sql}</pre>
        </dialog>
      ) : null}
    </>
  );
}

function FineReportReferenceTables({ items }) {
  const grouped = groupFineReportRefTables(items);

  return (
    <>
      {FINE_REPORT_REF_TABLE_GROUPS.map((group) => (
        <div className="sd-block" key={group.key}>
          <div className="subhead">
            <Icon name={group.icon} size={12} /> {group.label}
            <span className="sd-num mono">{grouped[group.key].length}</span>
          </div>
          <ReferenceTableList items={grouped[group.key]} stacked />
        </div>
      ))}
    </>
  );
}

function ReportDetailAccordion({ report, detailId, open, onClose }) {
  const audit = reportAudit(report);
  const type = reportType(report);
  const refTables = Array.isArray(report.refTables) ? report.refTables : [];
  const issues = sortAlertRows(report.issues);

  return (
    <section id={detailId} className={`detail-accordion${open ? " open" : ""}`} role="region" aria-label={`${report.title} 详情`} aria-hidden={!open} inert={open ? undefined : ""}>
      <div className="detail-accordion-content">
        <div className="sd-head">
          <div className="sd-head-top">
            <span className="sd-kicker"><Icon name={type.icon} size={13} /> {type.label}</span>
            <span className="sd-head-actions">
              <span className={`badge ${audit.level}`}>
                <Icon name={audit.level === "ok" ? "check" : audit.level === "err" ? "x" : "alert"} size={11} stroke={2.4} />
                {audit.level === "ok" ? "通过" : audit.err ? `${audit.err} 错误` : `${audit.warn} 警告`}
              </span>
              {report.previewUrl ? (
                <a className="btn ghost sm" href={report.previewUrl} target="_blank" rel="noreferrer"><Icon name="screen" size={13} /> 预览报表</a>
              ) : null}
              {report.downloadUrl ? (
                <a className="btn ghost sm" href={report.downloadUrl} target="_blank" rel="noreferrer"><Icon name="download" size={13} /> 下载代码</a>
              ) : null}
              <button className="iconbtn" style={{ width: 28, height: 28 }} onClick={onClose} aria-label="收起详情"><Icon name="x" size={15} /></button>
            </span>
          </div>
          <div className="sd-script">{report.title}</div>
          <div className="fr-path mono">{report.file}</div>
          <dl className="sd-meta">
            <div><dt>类型</dt><dd>{report.type === "frm" ? "决策大屏" : "普通报表"}</dd></div>
            <div><dt>数据源</dt><dd className="mono">{report.conn}</dd></div>
            {report.engine ? <div><dt>引擎</dt><dd>{report.engine}</dd></div> : null}
            {report.sheets?.length ? <div><dt>Sheet 页</dt><dd className="mono">{report.sheets.length} 个：{report.sheets.join(", ")}</dd></div> : null}
            <div><dt>数据集 / 引用表</dt><dd className="mono">{report.datasets.length} / {refTables.length}</dd></div>
          </dl>
        </div>

        <div className="sd-body">
          <div className="sd-focus">
            <span className="sd-focus-ic"><Icon name="search" size={14} /></span>
            <div>
              <div className="sd-focus-label">检查重点</div>
              <p className="sd-focus-text">{report.focus}</p>
            </div>
          </div>

          <div className="sd-block">
            <div className="subhead">
              <Icon name="search" size={12} /> 问题明细 <span className="sd-num mono">{issues.length}</span>
              <span className="sd-tally">
                {audit.err ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{audit.err} 个错误</span> : null}
                {audit.warn ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{audit.warn} 个警告</span> : null}
              </span>
            </div>
            <div className="table-wrap sd-cmp">
              <table className="tbl">
                <thead>
                  <tr>
                    <th style={{ width: 110 }}>类别</th>
                    <th style={{ width: 120 }}>位置</th>
                    <th>规则</th>
                    <th className="severity-cell">级别</th>
                    <th>说明</th>
                  </tr>
                </thead>
                <tbody>
                  {issues.map((issue, index) => {
                    const category = FR_CAT[issue.cat] || { label: issue.cat, icon: "info" };
                    return (
                      <tr key={index} className={issue.level === "err" ? "err-row" : issue.level === "warn" ? "warn-row" : ""}>
                        <td><span className="fr-cat"><Icon name={category.icon} size={12} />{category.label}</span></td>
                        <td className="mono" style={{ fontSize: "var(--fs-xs)" }}>{issue.loc}</td>
                        <td className="rule-cell">{issue.rule}</td>
                        <td className="severity-cell"><Sev level={issue.level} /></td>
                        <td>{issue.msg}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="sd-block">
            <div className="subhead"><Icon name="db" size={12} /> 数据集 <span className="sd-num mono">{report.datasets.length}</span></div>
            <div className="fr-ds-list">
              {report.datasets.map((dataset, index) => (
                <DatasetSqlCard key={`${dataset.name}-${index}`} dataset={dataset} index={index} />
              ))}
            </div>
          </div>

          {report.type === "cpt" ? <FineReportReferenceTables items={refTables} /> : null}
        </div>
      </div>
    </section>
  );
}

function mergeFineReportItems(baseData, items) {
  if (!items?.length) return baseData;
  const baseReports = new Map((baseData.reports || []).map((report) => [report.file, report]));
  const reports = items.map((item) => {
    const existing = baseReports.get(item.file_path) || {};
    return {
      ...existing,
      title: item.title,
      file: item.file_path,
      type: item.report_type,
      change: item.change_type,
      conn: item.connection_name,
      focus: item.focus,
      datasets: [{ name: "api_dataset", sql: item.dataset_sql || "SELECT ...", rows: item.dataset_rows || "about 1k" }],
      issues: item.issues || [],
      refTables: item.ref_tables || [],
    };
  });

  const errors = reports.flatMap((report) => report.issues).filter((issue) => issue.level === "err").length;
  const warnings = reports.flatMap((report) => report.issues).filter((issue) => issue.level === "warn").length;

  return {
    ...baseData,
    task: {
      ...baseData.task,
      reports: reports.length,
      errors,
      warnings,
      status: errors ? "fail" : warnings ? "warn" : "pass",
    },
    reports,
    refTables: reports.flatMap((report) => report.refTables),
  };
}

export function FineReportResultsPage({ d, aiEnabled, reg, apiState, reportDataPending = false }) {
  const dismissedReportIds = useRef(new Set());
  const [openReportIds, setOpenReportIds] = useState(() => (
    syncAutoOpenReportIds(new Set(), d.reports, dismissedReportIds.current)
  ));
  const mergedData = useMemo(() => mergeFineReportItems(d, apiState?.data), [d, apiState?.data]);

  const toggleReport = (reportId) => {
    setOpenReportIds((current) => {
      const next = new Set(current);
      if (next.has(reportId)) {
        next.delete(reportId);
        dismissedReportIds.current.add(reportId);
      } else {
        next.add(reportId);
        dismissedReportIds.current.delete(reportId);
      }
      return next;
    });
  };

  useEffect(() => {
    setOpenReportIds((current) => (
      syncAutoOpenReportIds(current, mergedData.reports, dismissedReportIds.current)
    ));
  }, [mergedData.reports]);

  useEffect(() => {
    const closeAll = (event) => {
      if (event.key === "Escape") {
        setOpenReportIds((current) => {
          current.forEach((reportId) => dismissedReportIds.current.add(reportId));
          return new Set();
        });
      }
    };
    window.addEventListener("keydown", closeAll);
    return () => window.removeEventListener("keydown", closeAll);
  }, []);

  return (
    <div className="results-page fade-in">
      {apiState?.loading ? <div className="card" style={{ padding: 14, marginBottom: "var(--gap)" }}>正在加载报表检查数据...</div> : null}
      {apiState?.error ? <div className="card" style={{ padding: 14, marginBottom: "var(--gap)", borderColor: "var(--err)" }}>FineReport API 不可用，请检查任务接口配置。</div> : null}
      <FrStatusHeader d={mergedData} />
      <FineChangesSection d={mergedData} reg={reg} />
      <TxtTableSection id="menu" icon="folder" title="目录检查（menu.txt）" section={mergedData.menu} reg={reg} />
      <TxtTableSection id="authority" icon="shield" title="权限检查（authority.txt）" section={mergedData.authority} reg={reg} />
      <ReportListSection
        d={mergedData}
        reg={reg}
        openReportIds={openReportIds}
        onToggle={toggleReport}
        loading={reportDataPending || Boolean(apiState?.loading)}
      />
      <AssetIssuesSection d={mergedData} reg={reg} />
      {aiEnabled ? <AiSection d={mergedData} reg={reg} /> : null}
    </div>
  );
}
