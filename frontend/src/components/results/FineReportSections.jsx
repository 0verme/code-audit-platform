import { Icon, OkState, Panel, Sev } from "../ui";
import { ReferenceTableList } from "../ReferenceTableList";
import { SourceFileLinks } from "../SourceFileLinks";
import { DatasetSqlCard } from "./FineReportDatasetSqlCard";
import { StatusHero } from "./StatusHero";
import { sortAlertRows } from "../../utils/alertSorting";
import {
  FINE_REPORT_REF_TABLE_GROUPS,
  getReportElementId,
  getReportKey,
  groupFineReportRefTables,
  reportAudit,
} from "../../utils/fineReportPresentation";

const FR_CAT = {
  dataset: { label: "数据集", icon: "db" },
  conn: { label: "连接", icon: "link" },
  param: { label: "参数", icon: "layers" },
  tpl: { label: "模板", icon: "grid" },
  perf: { label: "性能", icon: "gauge" },
  perm: { label: "权限", icon: "shield" },
};

function reportType(report) {
  return report.type === "frm"
    ? { icon: "screen", label: "决策大屏 .frm" }
    : { icon: "grid", label: "普通报表 .cpt" };
}

export function FrStatusHeader({ d }) {
  const task = d.task;
  const reports = Array.isArray(d.reports) ? d.reports : [];
  const highRisk = reports.filter((report) => reportAudit(report).err).length;
  return (
    <StatusHero
      data={d}
      workflowIcon="grid"
      durationLabel="时长"
      description={(currentTask, status) =>
        ["running", "starting", "failed"].includes(d.__auditRun?.pageStatus)
          ? status?.desc
          : currentTask.status === "pass"
            ? "所有报表均已通过检查，可以发布。"
            : "存在尚未解决的数据集、连接或权限问题。"
      }
      metrics={[
        { label: "报表", value: task.reports, icon: "grid" },
        { label: "检查项", value: task.checks, icon: "layers" },
        {
          label: "错误",
          value: task.errors,
          tone: task.errors ? "err" : "ok",
          icon: "x",
        },
        {
          label: "警告",
          value: task.warnings,
          tone: task.warnings ? "warn" : "ok",
          icon: "alert",
        },
        {
          label: "高风险",
          value: highRisk,
          tone: highRisk ? "err" : "ok",
          icon: "shield",
        },
      ]}
    />
  );
}

export function ReportListSection({
  d,
  reg,
  openReportIds,
  onToggle,
  loading = false,
}) {
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
            <div className="empty-state">
              本次审查未发现可展示的报表检查项。
            </div>
          ) : null}
          {!loading &&
            reports.map((report) => {
              const audit = reportAudit(report);
              const type = reportType(report);
              const reportKey = getReportKey(report);
              const reportElementId = getReportElementId(reportKey);
              const detailId = `${reportElementId}-detail`;
              const isOpen = openReportIds.has(reportKey);
              return (
                <div
                  id={reportElementId}
                  key={reportKey}
                  className={`accordion-item${isOpen ? " open" : ""}`}
                >
                  <button
                    className="fr-row"
                    onClick={() => onToggle(reportKey)}
                    aria-expanded={isOpen}
                    aria-controls={detailId}
                  >
                    <span className={`fr-ico ${report.type}`}>
                      <Icon name={type.icon} size={16} />
                    </span>
                    <span className="pas-main">
                      <span className="fr-name">
                        <span className={`chg-tag ${report.change}`}>
                          {report.change}
                        </span>
                        {report.title}
                      </span>
                      <span className="pas-sub mono">{report.file}</span>
                    </span>
                    <span className="fr-meta mono">
                      <span className="fr-type">
                        {report.type === "frm" ? "FRM" : "CPT"}
                      </span>
                      <span className="fr-dot">/</span>
                      <span>数据集 {report.datasets.length}</span>
                      <span className="fr-dot">/</span>
                      <span>
                        引用表{" "}
                        {Array.isArray(report.refTables)
                          ? report.refTables.length
                          : 0}
                      </span>
                    </span>
                    <span className="pas-tags">
                      <span className="pas-grp-label">检查</span>
                      {audit.err ? (
                        <span className="sev err">
                          <Icon name="x" size={11} stroke={2.4} />
                          {audit.err}
                        </span>
                      ) : null}
                      {audit.warn ? (
                        <span className="sev warn">
                          <Icon name="alert" size={11} stroke={2.4} />
                          {audit.warn}
                        </span>
                      ) : null}
                      {!audit.total ? (
                        <span className="sev ok">
                          <Icon name="check" size={11} stroke={2.4} />
                          通过
                        </span>
                      ) : null}
                    </span>
                    <Icon name="chevron" size={16} className="pas-chev" />
                  </button>
                  <ReportDetailAccordion
                    report={report}
                    detailId={detailId}
                    open={isOpen}
                    onClose={() => onToggle(reportKey)}
                  />
                </div>
              );
            })}
        </div>
      </div>
    </Panel>
  );
}

export function TxtTableSection({ id, icon, title, section, reg }) {
  if (!section) return null;
  const messages = section.messages || [];
  const sortedMessages = sortAlertRows(messages);
  const severity = messages.some((m) => m.level === "err")
    ? "err"
    : messages.some((m) => m.level === "warn")
      ? "warn"
      : "ok";
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
        files={
          section.downloadUrl
            ? [
                {
                  kind: id,
                  path: section.file,
                  name: section.file,
                  downloadUrl: section.downloadUrl,
                },
              ]
            : []
        }
      />
      <div className="panel-body">
        {section.rows?.length ? (
          <div
            className="table-wrap"
            style={{
              border: "1px solid var(--border)",
              borderRadius: 8,
              overflow: "hidden",
              marginBottom: messages.length ? 12 : 0,
            }}
          >
            <table className="tbl">
              <thead>
                <tr>
                  {section.columns.map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {section.rows.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {row.map((cell, cellIndex) => (
                      <td
                        key={cellIndex}
                        className="mono"
                        style={{ fontSize: "var(--fs-xs)" }}
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        {messages.length ? (
          <div
            className="table-wrap"
            style={{
              border: "1px solid var(--border)",
              borderRadius: 8,
              overflow: "hidden",
            }}
          >
            <table className="tbl">
              <thead>
                <tr>
                  <th style={{ width: 80 }}>级别</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                {sortedMessages.map((msg, index) => (
                  <tr
                    key={index}
                    className={
                      msg.level === "err"
                        ? "err-row"
                        : msg.level === "warn"
                          ? "warn-row"
                          : ""
                    }
                  >
                    <td className="severity-cell">
                      <Sev level={msg.level} />
                    </td>
                    <td>{msg.msg}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <OkState>校验通过</OkState>
        )}
      </div>
    </Panel>
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
    <section
      id={detailId}
      className={`detail-accordion${open ? " open" : ""}`}
      role="region"
      aria-label={`${report.title} 详情`}
      aria-hidden={!open}
      inert={open ? undefined : ""}
    >
      <div className="detail-accordion-content">
        <div className="sd-head">
          <div className="sd-head-top">
            <span className="sd-kicker">
              <Icon name={type.icon} size={13} /> {type.label}
            </span>
            <span className="sd-head-actions">
              <span className={`badge ${audit.level}`}>
                <Icon
                  name={
                    audit.level === "ok"
                      ? "check"
                      : audit.level === "err"
                        ? "x"
                        : "alert"
                  }
                  size={11}
                  stroke={2.4}
                />
                {audit.level === "ok"
                  ? "通过"
                  : audit.err
                    ? `${audit.err} 错误`
                    : `${audit.warn} 警告`}
              </span>
              {report.previewUrl ? (
                <a
                  className="btn ghost sm"
                  href={report.previewUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Icon name="screen" size={13} /> 预览报表
                </a>
              ) : null}
              {report.downloadUrl ? (
                <a
                  className="btn ghost sm"
                  href={report.downloadUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Icon name="download" size={13} /> 下载代码
                </a>
              ) : null}
              <button
                className="iconbtn"
                style={{ width: 28, height: 28 }}
                onClick={onClose}
                aria-label="收起详情"
              >
                <Icon name="x" size={15} />
              </button>
            </span>
          </div>
          <div className="sd-script">{report.title}</div>
          <div className="fr-path mono">{report.file}</div>
          <dl className="sd-meta">
            <div>
              <dt>类型</dt>
              <dd>{report.type === "frm" ? "决策大屏" : "普通报表"}</dd>
            </div>
            <div>
              <dt>数据源</dt>
              <dd className="mono">{report.conn}</dd>
            </div>
            {report.engine ? (
              <div>
                <dt>引擎</dt>
                <dd>{report.engine}</dd>
              </div>
            ) : null}
            {report.sheets?.length ? (
              <div>
                <dt>Sheet 页</dt>
                <dd className="mono">
                  {report.sheets.length} 个：{report.sheets.join(", ")}
                </dd>
              </div>
            ) : null}
            <div>
              <dt>数据集 / 引用表</dt>
              <dd className="mono">
                {report.datasets.length} / {refTables.length}
              </dd>
            </div>
          </dl>
        </div>

        <div className="sd-body">
          <div className="sd-focus">
            <span className="sd-focus-ic">
              <Icon name="search" size={14} />
            </span>
            <div>
              <div className="sd-focus-label">检查重点</div>
              <p className="sd-focus-text">{report.focus}</p>
            </div>
          </div>

          <div className="sd-block">
            <div className="subhead">
              <Icon name="search" size={12} /> 问题明细{" "}
              <span className="sd-num mono">{issues.length}</span>
              <span className="sd-tally">
                {audit.err ? (
                  <span className="sev err">
                    <Icon name="x" size={11} stroke={2.4} />
                    {audit.err} 个错误
                  </span>
                ) : null}
                {audit.warn ? (
                  <span className="sev warn">
                    <Icon name="alert" size={11} stroke={2.4} />
                    {audit.warn} 个警告
                  </span>
                ) : null}
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
                    const category = FR_CAT[issue.cat] || {
                      label: issue.cat,
                      icon: "info",
                    };
                    return (
                      <tr
                        key={index}
                        className={
                          issue.level === "err"
                            ? "err-row"
                            : issue.level === "warn"
                              ? "warn-row"
                              : ""
                        }
                      >
                        <td>
                          <span className="fr-cat">
                            <Icon name={category.icon} size={12} />
                            {category.label}
                          </span>
                        </td>
                        <td
                          className="mono"
                          style={{ fontSize: "var(--fs-xs)" }}
                        >
                          {issue.loc}
                        </td>
                        <td className="rule-cell">{issue.rule}</td>
                        <td className="severity-cell">
                          <Sev level={issue.level} />
                        </td>
                        <td>{issue.msg}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="sd-block">
            <div className="subhead">
              <Icon name="db" size={12} /> 数据集{" "}
              <span className="sd-num mono">{report.datasets.length}</span>
            </div>
            <div className="fr-ds-list">
              {report.datasets.map((dataset, index) => (
                <DatasetSqlCard
                  key={`${dataset.name}-${index}`}
                  dataset={dataset}
                  index={index}
                />
              ))}
            </div>
          </div>

          {report.type === "cpt" ? (
            <FineReportReferenceTables items={refTables} />
          ) : null}
        </div>
      </div>
    </section>
  );
}
