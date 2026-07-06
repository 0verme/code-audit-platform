import { useEffect, useMemo, useState } from "react";
import { Badge, Icon, Metric, OkState, Panel, Sev } from "../components/ui";
import { AiSection, AssetIssuesSection, STATUS_META } from "./ResultsPage";

const FR_CAT = {
  dataset: { label: "Dataset", icon: "db" },
  conn: { label: "Connection", icon: "link" },
  param: { label: "Parameter", icon: "layers" },
  tpl: { label: "Template", icon: "grid" },
  perf: { label: "Performance", icon: "gauge" },
  perm: { label: "Permission", icon: "shield" },
};

const FR_REF_TYPES = [
  { key: "result", label: "Result Table", cls: "result" },
  { key: "mid", label: "Middle Table", cls: "mid" },
  { key: "src", label: "Source Table", cls: "src" },
  { key: "temp", label: "Temp Table", cls: "temp" },
];

export const FR_NAV = [
  { id: "overview", label: "Overview", icon: "layers" },
  { id: "reports", label: "Report Checks", icon: "grid", get: (data) => data.reports, neutral: true },
  { id: "reftables", label: "Referenced Tables", icon: "db", get: (data) => data.refTables, neutral: true },
];

function reportAudit(report) {
  const issues = report.issues || [];
  const err = issues.filter((item) => item.level === "err").length;
  const warn = issues.filter((item) => item.level === "warn").length;
  return { err, warn, total: issues.length, level: err ? "err" : warn ? "warn" : "ok" };
}

function reportType(report) {
  return report.type === "frm"
    ? { icon: "screen", label: "Decision Screen .frm" }
    : { icon: "grid", label: "Standard Report .cpt" };
}

function FrStatusHeader({ d }) {
  const task = d.task;
  const status = STATUS_META[task.status] || STATUS_META.warn;
  const highRisk = d.reports.filter((report) => reportAudit(report).err).length;
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
              ? "All reports passed validation and are ready to publish."
              : "There are unresolved dataset, connection, or permission issues."}
          </p>
          <div className="sh-meta mono">
            <span><Icon name="branch" size={12} /> {task.revision}</span>
            <span className="sh-sep">/</span>
            <span>{task.author}</span>
            <span className="sh-sep">/</span>
            <span><Icon name="clock" size={12} /> {task.startedAt}</span>
            <span className="sh-sep">/</span>
            <span>Duration {task.duration}</span>
          </div>
        </div>
      </div>
      <div className="metrics sh-metrics">
        <Metric label="Reports" value={task.reports} icon="grid" />
        <Metric label="Checks" value={task.checks} icon="layers" />
        <Metric label="Errors" value={task.errors} tone={task.errors ? "err" : "ok"} icon="x" />
        <Metric label="Warnings" value={task.warnings} tone={task.warnings ? "warn" : "ok"} icon="alert" />
        <Metric label="High Risk" value={highRisk} tone={highRisk ? "err" : "ok"} icon="shield" />
      </div>
    </div>
  );
}

function ReportListSection({ d, reg, onOpen }) {
  const reports = d.reports || [];
  const flagged = reports.filter((report) => reportAudit(report).total).length;
  const anyErr = reports.some((report) => reportAudit(report).err);

  return (
    <Panel
      id="reports"
      icon="grid"
      title="Report Review List"
      registerRef={reg}
      sub="Dataset / Connection / Parameter / Template / Performance / Permission"
      count={flagged ? `${flagged} reports need fixes` : "All passed"}
      countTone={flagged ? (anyErr ? "err" : "warn") : "ok"}
    >
      <div className="panel-body flush">
        <div className="pas-list">
          {reports.map((report) => {
            const audit = reportAudit(report);
            const type = reportType(report);
            return (
              <button key={report.file} className="fr-row" onClick={() => onOpen(report)}>
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
                  <span>Datasets {report.datasets.length}</span>
                  <span className="fr-dot">/</span>
                  <span>Refs {report.refTables.length}</span>
                </span>
                <span className="pas-tags">
                  <span className="pas-grp-label">Check</span>
                  {audit.err ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{audit.err}</span> : null}
                  {audit.warn ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{audit.warn}</span> : null}
                  {!audit.total ? <span className="sev ok"><Icon name="check" size={11} stroke={2.4} />Pass</span> : null}
                </span>
                <Icon name="chevron" size={16} className="pas-chev" />
              </button>
            );
          })}
        </div>
      </div>
    </Panel>
  );
}

function FrRefTablesSection({ d, reg }) {
  return (
    <Panel
      id="reftables"
      icon="db"
      title="Referenced Tables"
      registerRef={reg}
      count={d.refTables.length}
      sub="Grouped by table type"
    >
      <div className="panel-body">
        <div className="legend" style={{ marginBottom: 14 }}>
          {FR_REF_TYPES.map((type) => {
            const count = d.refTables.filter((item) => item.type === type.key).length;
            if (!count) return null;
            return (
              <span key={type.key} className="lg-item">
                <span className={`chip ${type.cls}`}><span className="cdot" />{type.label}</span>
                <span className="mono" style={{ color: "var(--text-3)" }}>x{count}</span>
              </span>
            );
          })}
        </div>
        {FR_REF_TYPES.map((type) => {
          const items = d.refTables.filter((item) => item.type === type.key);
          if (!items.length) return null;
          return (
            <div key={type.key} style={{ marginBottom: 12 }}>
              <div className="subhead" style={{ marginBottom: 7 }}>{type.label} / {items.length}</div>
              <div className="chips">
                {items.map((item) => (
                  <span key={item.name} className={`chip ${type.cls}`}>
                    <span className="cdot" />{item.name}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function TxtTableSection({ id, icon, title, section, reg }) {
  if (!section) return null;
  const messages = section.messages || [];
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
          <div className="fr-issue-list">
            {messages.map((msg, index) => (
              <div key={index} className={`ai-finding ${msg.level}`} style={{ marginBottom: 6 }}>
                <Sev level={msg.level} />
                <div className="aif-body"><div className="aif-text">{msg.msg}</div></div>
              </div>
            ))}
          </div>
        ) : <OkState>校验通过</OkState>}
      </div>
    </Panel>
  );
}

function ReportDetailDrawer({ report, onClose }) {
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const handle = requestAnimationFrame(() => setShown(true));
    return () => cancelAnimationFrame(handle);
  }, []);

  useEffect(() => {
    const handler = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const audit = reportAudit(report);
  const type = reportType(report);
  const issues = [...(report.issues || [])].sort(
    (left, right) => (left.level === "err" ? 0 : 1) - (right.level === "err" ? 0 : 1),
  );

  return (
    <div className={`sd-overlay${shown ? " shown" : ""}`} onClick={onClose}>
      <div className="sd-drawer" onClick={(event) => event.stopPropagation()}>
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
              <button className="iconbtn" style={{ width: 28, height: 28 }} onClick={onClose}><Icon name="x" size={15} /></button>
            </span>
          </div>
          <div className="sd-script">{report.title}</div>
          <div className="fr-path mono">{report.file}</div>
          <dl className="sd-meta">
            <div><dt>类型</dt><dd>{report.type === "frm" ? "决策大屏" : "普通报表"}</dd></div>
            <div><dt>数据源</dt><dd className="mono">{report.conn}</dd></div>
            {report.engine ? <div><dt>引擎</dt><dd>{report.engine}</dd></div> : null}
            {report.sheets?.length ? <div><dt>Sheet 页</dt><dd className="mono">{report.sheets.length} 个：{report.sheets.join(", ")}</dd></div> : null}
            <div><dt>数据集 / 引用表</dt><dd className="mono">{report.datasets.length} / {report.refTables.length}</dd></div>
          </dl>
        </div>

        <div className="sd-body">
          <div className="sd-focus">
            <span className="sd-focus-ic"><Icon name="search" size={14} /></span>
            <div>
              <div className="sd-focus-label">Review Focus</div>
              <p className="sd-focus-text">{report.focus}</p>
            </div>
          </div>

          <div className="sd-block">
            <div className="subhead">
              <Icon name="search" size={12} /> Issues <span className="sd-num mono">{issues.length}</span>
              <span className="sd-tally">
                {audit.err ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{audit.err} errors</span> : null}
                {audit.warn ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{audit.warn} warnings</span> : null}
              </span>
            </div>
            <div className="table-wrap sd-cmp">
              <table className="tbl">
                <thead>
                  <tr>
                    <th style={{ width: 110 }}>Category</th>
                    <th style={{ width: 120 }}>Location</th>
                    <th>Rule</th>
                    <th className="severity-cell">Level</th>
                    <th>Message</th>
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
            <div className="subhead"><Icon name="db" size={12} /> Datasets <span className="sd-num mono">{report.datasets.length}</span></div>
            <div className="fr-ds-list">
              {report.datasets.map((dataset) => (
                <div key={dataset.name} className="fr-ds">
                  <div className="fr-ds-top">
                    <span className="fr-ds-name mono">{dataset.name}</span>
                    <span className="fr-ds-rows mono">{dataset.rows} rows</span>
                  </div>
                  <pre className="fr-ds-sql mono">{dataset.sql}</pre>
                </div>
              ))}
            </div>
          </div>

          <div className="sd-block">
            <div className="subhead"><Icon name="db" size={12} /> Referenced Tables <span className="sd-num mono">{report.refTables.length}</span></div>
            <div className="chips">
              {report.refTables.map((item) => (
                <span
                  key={item.name}
                  className={`chip ${item.type === "result" ? "result" : item.type === "mid" ? "mid" : "src"}`}
                  style={item.highlight ? { color: "var(--err-fg)", fontWeight: 700 } : undefined}
                >
                  <span className="cdot" />{item.name}
                  {item.disabled ? "（禁用）" : item.sysNames?.length ? `（${item.sysNames.join("/")}）` : ""}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function mergeFineReportItems(baseData, items) {
  if (!items?.length) return baseData;
  const reports = items.map((item) => ({
    title: item.title,
    file: item.file_path,
    type: item.report_type,
    change: item.change_type,
    conn: item.connection_name,
    focus: item.focus,
    datasets: [{ name: "api_dataset", sql: item.dataset_sql || "SELECT ...", rows: item.dataset_rows || "about 1k" }],
    issues: item.issues || [],
    refTables: item.ref_tables || [],
  }));

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

export function FineReportResultsPage({ d, aiEnabled, reg, apiState }) {
  const [openReport, setOpenReport] = useState(null);
  const mergedData = useMemo(() => mergeFineReportItems(d, apiState?.data), [d, apiState?.data]);

  return (
    <div className="results-page fade-in">
      {apiState?.loading ? <div className="card" style={{ padding: 14, marginBottom: "var(--gap)" }}>Loading FineReport items...</div> : null}
      {apiState?.error ? <div className="card" style={{ padding: 14, marginBottom: "var(--gap)", borderColor: "var(--err)" }}>FineReport API 不可用，请检查任务接口配置。</div> : null}
      <FrStatusHeader d={mergedData} />
      <TxtTableSection id="menu" icon="folder" title="目录检查（menu.txt）" section={mergedData.menu} reg={reg} />
      <TxtTableSection id="authority" icon="shield" title="权限检查（authority.txt）" section={mergedData.authority} reg={reg} />
      <ReportListSection d={mergedData} reg={reg} onOpen={setOpenReport} />
      <FrRefTablesSection d={mergedData} reg={reg} />
      <AssetIssuesSection d={mergedData} reg={reg} />
      {aiEnabled ? <AiSection d={mergedData} reg={reg} /> : null}
      {openReport ? <ReportDetailDrawer report={openReport} onClose={() => setOpenReport(null)} /> : null}
    </div>
  );
}
