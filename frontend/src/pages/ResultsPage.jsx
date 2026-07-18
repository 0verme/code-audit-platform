import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { Badge, Dot, Icon, levelOf, Metric, OkState, Panel, Sev, ViolationTable } from "../components/ui";
import { LineageCanvas } from "../components/lineage/LineageCanvas";
import { toCycleDependencyGraph } from "../components/lineage/lineageAdapter";
import { shouldDefaultOpenChangeList } from "../utils/changeListPresentation";
import { syncAutoOpenScriptIds } from "../utils/scriptAuditPresentation";
import { sortAlertRows } from "../utils/alertSorting";
import { PyScriptAuditSection } from "./ScriptAudit";
import {
  getCycleDependencyFindings,
  getPythonIssueRows,
  getScheduleIssuesByTable,
  getScheduleIssueRows,
  getScheduleTableRows,
  hasScheduleTables,
} from "../utils/hcytResultPresentation";

export const STATUS_META = {
  pass: { tone: "ok", icon: "check", label: "审查通过", desc: "未发现阻断性问题，可合并" },
  fail: { tone: "err", icon: "x", label: "审查未通过", desc: "存在需要修复的阻断性问题" },
  warn: { tone: "warn", icon: "alert", label: "审查通过（含警告）", desc: "存在建议修复的告警项" },
};

STATUS_META.running = { tone: "info", icon: "clock", label: "审查执行中", desc: "审查结果正在异步生成，已完成模块会逐步填充到报告中。" };
STATUS_META.taskFailed = { tone: "err", icon: "x", label: "任务异常", desc: "审查任务异常结束，已完成模块仍可查看。" };

export const SECTION_NAV = [
  { id: "overview", label: "概览", icon: "layers" },
  { id: "changes", label: "变更文件", icon: "git", get: (data) => data.changes, neutral: true },
  { id: "conflict", label: "trunk 冲突", icon: "conflict", get: (data) => data.conflicts },
  { id: "dws", label: "DWS SQL", icon: "db", get: (data) => data.dws },
  { id: "hive", label: "Hive SQL", icon: "db", get: (data) => data.hive },
  { id: "config", label: "配置文件", icon: "cog", get: (data) => data.config },
  { id: "sbin", label: "后置脚本", icon: "terminal", get: (data) => data.sbin },
  { id: "recv", label: "收卸配置", icon: "download", get: (data) => data.recv },
  {
    id: "schedule",
    label: "调度表检查",
    icon: "grid",
    get: getScheduleIssueRows,
  },
  {
    id: "python",
    label: "Python 脚本",
    icon: "python",
    get: (data) => {
      return getPythonIssueRows(data);
    },
    neutral: true,
  },
];

function StatusHeader({ d }) {
  const run = d.__auditRun;
  const status =
    run?.pageStatus === "running" || run?.pageStatus === "starting"
      ? STATUS_META.running
      : run?.pageStatus === "failed"
        ? STATUS_META.taskFailed
        : STATUS_META[d.task.status] || STATUS_META.warn;
  const task = d.task;
  return (
    <div className={`status-hero card ${status.tone}`}>
      <div className="sh-main">
        <div className={`sh-badge ${status.tone}`}><Icon name={status.icon} size={26} stroke={2.4} /></div>
        <div className="sh-text">
          <div className="sh-title-row">
            <h2 className="sh-title">{status.label}</h2>
            <Badge tone="accent" icon="db">{task.workflow}</Badge>
          </div>
          <p className="sh-desc">{status.desc}</p>
          <div className="sh-meta mono">
            <span><Icon name="branch" size={12} /> {task.revision}</span>
            <span className="sh-sep">/</span>
            <span>{task.author}</span>
            <span className="sh-sep">/</span>
            <span><Icon name="clock" size={12} /> {task.startedAt}</span>
            <span className="sh-sep">/</span>
            <span>耗时 {task.duration}</span>
          </div>
        </div>
      </div>
      <div className="metrics sh-metrics">
        <Metric label="变更文件" value={task.changedFiles} icon="file" />
        <Metric label="检查项" value={task.checks} icon="layers" />
        <Metric label="错误" value={task.errors} tone={task.errors ? "err" : "ok"} icon="x" />
        <Metric label="警告" value={task.warnings} tone={task.warnings ? "warn" : "ok"} icon="alert" />
        <Metric label="冲突" value={task.conflicts} tone={task.conflicts ? "err" : "ok"} icon="conflict" />
      </div>
    </div>
  );
}

const MODULE_TASKS = [
  { key: "source_load", section: "changes", label: "读取工作区 / SVN", icon: "download" },
  { key: "classify_files", section: "changes", label: "变更文件", icon: "git" },
  { key: "trunk_conflicts", section: "conflict", label: "trunk 冲突", icon: "conflict" },
  { key: "dws_sql", section: "dws", label: "DWS SQL", icon: "db" },
  { key: "hive_sql", section: "hive", label: "Hive SQL", icon: "db" },
  { key: "config_files", section: "config", label: "配置文件", icon: "cog" },
  { key: "post_scripts", section: "sbin", label: "后置脚本", icon: "terminal" },
  { key: "recv_config", section: "recv", label: "收卸配置", icon: "download" },
  { key: "schedule", section: "schedule", label: "调度表检查", icon: "grid" },
  { key: "python_scripts", section: "python", label: "Python 脚本", icon: "python" },
  { key: "lineage", section: "lineage-summary", label: "依赖链分析", icon: "flow" },
  { key: "summary", section: "overview", label: "保存审查报告", icon: "check" },
];

const TASK_STATUS_META = {
  queued: { tone: "", label: "排队中" },
  running: { tone: "info", label: "执行中" },
  success: { tone: "ok", label: "已完成" },
  skipped: { tone: "warn", label: "已跳过" },
  failed: { tone: "err", label: "检查异常" },
};

function formatDurationMs(value) {
  if (value == null) return "";
  const seconds = Math.round(Number(value) / 1000);
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function elapsedSince(value) {
  if (!value) return "0s";
  const started = new Date(value).getTime();
  if (!Number.isFinite(started)) return "0s";
  return formatDurationMs(Math.max(0, Date.now() - started));
}

function ProgressiveRunPanel({ d }) {
  const run = d.__auditRun;
  if (!run || run.finalReportReady) return null;
  const tasks = run.tasks || {};
  const taskValues = Object.values(tasks);
  const completed = taskValues.filter((task) => ["success", "skipped", "failed"].includes(task.status)).length;
  const total = run.progress?.total || taskValues.length || MODULE_TASKS.length;
  const percent = Math.max(0, Math.min(100, Number(run.progress?.percent || 0)));
  const failed = run.progress?.failed ?? taskValues.filter((task) => task.status === "failed").length;
  const skipped = run.progress?.skipped ?? taskValues.filter((task) => task.status === "skipped").length;
  const elapsed = elapsedSince(run.statusPayload?.startedAt || run.statusPayload?.task?.started_at || d.task.startedAt);

  return (
    <div className={`card progressive-run ${run.pageStatus === "failed" ? "failed" : ""}`}>
      <div className="progressive-main">
        <div>
          <div className="section-title"><Icon name={run.pageStatus === "failed" ? "x" : "clock"} size={16} /> {run.pageStatus === "failed" ? "任务异常" : "审查执行中"}</div>
          <div className="progressive-sub">当前模块：{run.currentModule || "等待调度"} · 已完成 {completed}/{total} · 耗时 {elapsed}</div>
        </div>
        <div className="progressive-counts">
          <Badge tone={d.task.errors ? "err" : "ok"} mono>错误 {d.task.errors || 0}</Badge>
          <Badge tone={d.task.warnings ? "warn" : "ok"} mono>警告 {d.task.warnings || 0}</Badge>
          <Badge tone={d.task.conflicts ? "err" : "ok"} mono>冲突 {d.task.conflicts || 0}</Badge>
          {failed ? <Badge tone="err" mono>异常 {failed}</Badge> : null}
          {skipped ? <Badge tone="warn" mono>跳过 {skipped}</Badge> : null}
        </div>
      </div>
      <div className="real-progress" aria-label="审查进度">
        <span style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function ModuleProgressBoard({ d, onJump }) {
  const run = d.__auditRun;
  if (!run) return null;
  const tasks = run.tasks || {};

  return (
    <div className="card module-progress-board">
      <div className="subhead"><Icon name="grid" size={12} /> 模块执行状态</div>
      <div className="module-progress-grid">
        {MODULE_TASKS.map((module) => {
          const state = tasks[module.key] || {};
          const status = state.status || "queued";
          const meta = TASK_STATUS_META[status] || TASK_STATUS_META.queued;
          const duration = formatDurationMs(state.durationMs);
          return (
            <button key={module.key} className={`module-progress-card ${status}`} onClick={() => onJump(module.section)}>
              <span className="mp-icon"><Icon name={module.icon} size={14} /></span>
              <span className="mp-body">
                <span className="mp-title">{module.label}</span>
                <span className="mp-meta">
                  <Badge tone={meta.tone} mono>{meta.label}</Badge>
                  {duration ? <span>{duration}</span> : null}
                  {status === "running" && state.startedAt ? <span>当前 {elapsedSince(state.startedAt)}</span> : null}
                  {Number(state.durationMs) > 10000 ? <span className="slow-hint">耗时较长</span> : null}
                </span>
                {state.error ? <span className="mp-error">{state.error}</span> : null}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function RunLogs({ d }) {
  const logs = d.__auditRun?.logs || d.logs || [];
  if (!logs.length) return null;
  return (
    <details className="card run-logs">
      <summary><Icon name="terminal" size={13} /> 查看执行日志 <Badge mono>{logs.length}</Badge></summary>
      <pre className="mono">
        {logs.slice(-80).map((entry, index) => `[${entry.ts || "-"}] ${entry.level || "INFO"} ${entry.msg || entry.message || ""}`).join("\n")}
      </pre>
    </details>
  );
}

function ChangesSection({ d, reg }) {
  if (!d.changes.length) return null;

  const counts = d.changes.reduce((accumulator, item) => {
    accumulator[item.type] = (accumulator[item.type] || 0) + 1;
    return accumulator;
  }, {});

  return (
    <Panel
      id="changes"
      icon="git"
      title="SVN 变更文件列表"
      registerRef={reg}
      count={d.changes.length}
      countTone="info"
      defaultOpen={shouldDefaultOpenChangeList(d.changes.length)}
      right={
        <span className="diffstat" style={{ marginRight: 4 }}>
          <span className="add mono">A {counts.A || 0}</span>
          <span className="del mono" style={{ color: "var(--info-fg)" }}>M {counts.M || 0}</span>
        </span>
      }
    >
      <div className="panel-body flush">
        <div className="flist">
          {d.changes.map((change) => {
            const index = change.path.lastIndexOf("/") + 1;
            const dir = change.path.slice(0, index);
            const name = change.path.slice(index);
            const hasDiff = change.add != null || change.del != null;
            return (
              <div key={change.path} className="frow">
                <span className={`chg-tag ${change.type}`}>{change.type}</span>
                <span className="fpath"><span className="fdir">{dir}</span>{name}</span>
                <Badge>{change.cat}</Badge>
                {hasDiff ? (
                  <span className="diffstat">
                    <span className="add">+{change.add || 0}</span>
                    <span className="del">-{change.del || 0}</span>
                  </span>
                ) : null}
                {change.downloadUrl ? (
                  <a className="dl-link" href={change.downloadUrl} target="_blank" rel="noreferrer">
                    <Icon name="download" size={12} /> 下载
                  </a>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    </Panel>
  );
}

function ConflictSection({ d, reg }) {
  const hasConflicts = d.conflicts.length > 0;
  if (!hasConflicts) return null;

  return (
    <Panel
      id="conflict"
      icon="conflict"
      title="trunk 重叠冲突文件"
      registerRef={reg}
      count={d.conflicts.length}
      countTone={hasConflicts ? "err" : "ok"}
      defaultOpen={hasConflicts}
      sub={hasConflicts ? "与主干内容存在重叠" : null}
    >
      <div className="panel-body">
        {hasConflicts ? (
          <div className="flist conflict-list">
            {d.conflicts.map((conflict) => (
              <div key={conflict.path} className="frow conflict" style={{ height: "auto", padding: "10px 12px" }}>
                <Icon name="conflict" size={15} style={{ color: "var(--err)", flex: "none" }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="fpath" style={{ color: "var(--err-fg)" }}>{conflict.path}</div>
                  <div style={{ fontSize: "var(--fs-xs)", color: "var(--text-2)", marginTop: 3 }}>{conflict.note}</div>
                </div>
                <div className="diffstat" style={{ flexDirection: "column", gap: 2, textAlign: "right" }}>
                  <span className="mono" style={{ color: "var(--text-3)" }}>trunk {conflict.trunkRev}</span>
                  <span className="mono" style={{ color: "var(--err-fg)" }}>本次 {conflict.mineRev}</span>
                </div>
              </div>
            ))}
          </div>
        ) : <OkState>未检测到与 trunk 主干的重叠冲突</OkState>}
      </div>
    </Panel>
  );
}

function CheckSection({ id, icon, title, rows, reg, okMsg, scriptMeta }) {
  if (!rows.length) return null;

  const severity = levelOf(rows);
  const errs = rows.filter((row) => row.level === "err").length;
  const warns = rows.filter((row) => row.level === "warn").length;

  return (
    <Panel
      id={id}
      icon={icon}
      title={title}
      accentHeader
      registerRef={reg}
      count={rows.length || "通过"}
      countTone={severity || "ok"}
      defaultOpen={rows.length > 0}
      right={
        rows.length ? (
          <span className="mini-counts">
            {errs ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{errs}</span> : null}
            {warns ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{warns}</span> : null}
          </span>
        ) : null
      }
    >
      {scriptMeta?.script ? (
        <div className="script-bar">
          <Icon name="file" size={12} /> 检查脚本：<span className="mono">{scriptMeta.script}</span>
          {scriptMeta.downloadUrl ? (
            <a
              className="dl-link"
              href={scriptMeta.downloadUrl}
              target="_blank"
              rel="noreferrer"
            >
              <Icon name="download" size={12} /> 下载代码
            </a>
          ) : null}
        </div>
      ) : null}
      <div className={rows.length ? "panel-body flush" : "panel-body"}>
        {rows.length ? <ViolationTable rows={rows} /> : <OkState>{okMsg || "未发现违规项"}</OkState>}
      </div>
    </Panel>
  );
}

function ConfigFilesDetail({ files, detailId }) {
  return (
    <tr className="config-detail-row">
      <td colSpan={4}>
        <section id={detailId} className="config-detail fade-in" role="region" aria-label="SCHEMA_CONFIG 详情">
          {files.map((file, fileIndex) => (
            <div key={`${file.name}-${fileIndex}`} className="config-file-detail">
              <div className="subhead"><Icon name="file" size={12} /> {file.name}</div>
              {file.error ? (
                <div className="sd-empty">{file.error}</div>
              ) : (
                <div className="table-wrap">
                  <table className="tbl">
                    <thead><tr>{file.columns.map((col) => <th key={col}>{col}</th>)}</tr></thead>
                    <tbody>
                      {file.rows.map((row, rowIndex) => (
                        <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={cellIndex} className="mono">{cell}</td>)}</tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </section>
      </td>
    </tr>
  );
}

export function ConfigCheckSection({ rows = [], files = [], reg }) {
  const [openRowIndex, setOpenRowIndex] = useState(null);
  if (!rows.length && !files.length) return null;

  const displayRows = rows.length ? sortAlertRows(rows) : [{
    file: "SCHEMA_CONFIG",
    rule: "",
    level: "ok",
    msg: "Schema 配置文件校验通过",
  }];
  const severity = levelOf(rows);
  const errs = rows.filter((row) => row.level === "err").length;
  const warns = rows.filter((row) => row.level === "warn").length;
  const toggleRow = (rowIndex) => setOpenRowIndex((current) => current === rowIndex ? null : rowIndex);

  return (
    <Panel
      id="config"
      icon="cog"
      title="配置文件检查"
      accentHeader
      registerRef={reg}
      count={rows.length || "通过"}
      countTone={severity || "ok"}
      right={
        rows.length ? (
          <span className="mini-counts">
            {errs ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{errs}</span> : null}
            {warns ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{warns}</span> : null}
          </span>
        ) : null
      }
    >
      <div className="panel-body flush">
        <div className="table-wrap">
          <table className="tbl config-check-table">
            <thead>
              <tr><th>文件</th><th>规则</th><th className="severity-cell">级别</th><th>说明</th></tr>
            </thead>
            <tbody>
              {displayRows.map((row, rowIndex) => {
                const canExpand = files.length > 0 && String(row.file || "").toUpperCase() === "SCHEMA_CONFIG";
                const isOpen = canExpand && openRowIndex === rowIndex;
                const detailId = `config-detail-${rowIndex}`;
                return (
                  <Fragment key={`config-item-${rowIndex}`}>
                    <tr
                      className={`${row.level === "err" ? "err-row" : row.level === "warn" ? "warn-row" : ""}${canExpand ? " config-check-row" : ""}${isOpen ? " open" : ""}`}
                      onClick={canExpand ? () => toggleRow(rowIndex) : undefined}
                    >
                      <td className="file-cell">
                        {canExpand ? (
                          <button
                            type="button"
                            className="config-file-trigger mono"
                            onClick={(event) => { event.stopPropagation(); toggleRow(rowIndex); }}
                            aria-expanded={isOpen}
                            aria-controls={detailId}
                          >
                            <Icon name="chevron" size={14} className="config-row-chev" />
                            {row.file}
                          </button>
                        ) : <span className="mono">{row.file}</span>}
                      </td>
                      <td className="rule-cell">{row.rule}</td>
                      <td className="severity-cell"><Sev level={row.level} /></td>
                      <td>{row.msg}</td>
                    </tr>
                    {isOpen ? <ConfigFilesDetail files={files} detailId={detailId} /> : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </Panel>
  );
}

export function AssetIssuesSection({ d, reg }) {
  const issues = d.assetIssues || [];
  if (!issues.length) return null;

  return (
    <Panel
      id="asset-issues"
      icon="link"
      title="资产问题"
      accentHeader
      registerRef={reg}
      count={issues.length}
      countTone="warn"
      defaultOpen
    >
      <div className="panel-body flush">
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>类型</th>
                <th>对象</th>
                <th>说明</th>
                <th>门户</th>
              </tr>
            </thead>
            <tbody>
              {issues.map((issue) => {
                const objectName = issue.objectName || [issue.schemaName, issue.tableName, issue.fieldName].filter(Boolean).join(".") || issue.rootWord || "-";
                return (
                  <tr key={issue.issueKey || issue.hashKey || `${issue.issueType}-${objectName}`} className="warn-row">
                    <td><Badge tone="warn">{issue.issueTitle || issue.issueType}</Badge></td>
                    <td className="mono" style={{ fontSize: "var(--fs-xs)" }}>{objectName}</td>
                    <td>{issue.issueDesc}</td>
                    <td>
                      {issue.portalUrl ? (
                        <a className="dl-link" href={issue.portalUrl} target="_blank" rel="noreferrer">
                          <Icon name="link" size={12} /> {issue.actionLabel || "打开"}
                        </a>
                      ) : <span style={{ color: "var(--text-3)" }}>未配置</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </Panel>
  );
}

const LINEAGE_LISTS = [
  { key: "resultTables", label: "结果表" },
  { key: "jobs", label: "作业" },
  { key: "recvPlans", label: "上游卸数计划" },
  { key: "sysNames", label: "来源系统" },
  { key: "outfiles", label: "下游 outfile" },
];

const LINEAGE_VALUE_KEYS = ["name", "tableName", "jobName", "planName", "sysName", "outfile", "value"];
const SENSITIVE_KEY_RE = /(password|passwd|pwd|token|secret|credential|account|username|user|conn|connect|jdbc|dsn|url|host|ip|addr|address)/i;
const IPV4_RE = /\b(?:\d{1,3}\.){3}\d{1,3}\b/g;
const CONNECTION_TEXT_RE = /\b(?:jdbc|odbc|oracle|mysql|postgresql|postgres|gaussdb|mongodb|redis|sqlserver):[^\s,;)}]+/gi;
const DSN_TEXT_RE = /\b(?:dsn|conn|connection|connectionString|url)\s*[:=]\s*[^\s,;)}]+/gi;
const SECRET_TEXT_RE = /\b(password|passwd|pwd|token|secret|credential)\s*[:=]\s*[^\s,;)}]+/gi;

export function maskSensitiveText(value) {
  const text = String(value ?? "");
  return text
    .replace(CONNECTION_TEXT_RE, "[masked-connection]")
    .replace(DSN_TEXT_RE, "[masked-connection]")
    .replace(IPV4_RE, "[masked-ip]")
    .replace(SECRET_TEXT_RE, "$1=[masked]");
}

function shortenLineageText(value, maxLength = 120) {
  const text = maskSensitiveText(value).trim();
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
}

export function normalizeLineageList(value) {
  return Array.isArray(value) ? value : [];
}

export function normalizeLineageStats(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return [];
  return Object.entries(value)
    .filter(([key]) => !SENSITIVE_KEY_RE.test(key))
    .map(([key, statValue]) => [shortenLineageText(key, 40), shortenLineageText(statValue, 40)]);
}

export function formatLineageItem(item) {
  if (item == null) return "-";
  if (typeof item !== "object") return shortenLineageText(item);

  for (const key of LINEAGE_VALUE_KEYS) {
    if (!SENSITIVE_KEY_RE.test(key) && item[key] != null && item[key] !== "") {
      return shortenLineageText(item[key]);
    }
  }

  const safeObject = Object.fromEntries(
    Object.entries(item)
      .filter(([key, value]) => !SENSITIVE_KEY_RE.test(key) && value != null && value !== "")
      .slice(0, 4)
  );
  return Object.keys(safeObject).length ? shortenLineageText(JSON.stringify(safeObject), 160) : "-";
}

function LineageList({ label, items }) {
  return (
    <div style={{ minWidth: 0 }}>
      <div className="subhead" style={{ marginBottom: 7 }}>{label}</div>
      {items.length ? (
        <div className="chips">
          {items.map((item, index) => (
            <span
              key={`${label}-${index}-${formatLineageItem(item)}`}
              className="chip src"
              style={{ maxWidth: "100%", whiteSpace: "normal", overflowWrap: "anywhere" }}
            >
              <span className="cdot" />
              {formatLineageItem(item)}
            </span>
          ))}
        </div>
      ) : (
        <div className="sd-empty">暂无数据</div>
      )}
    </div>
  );
}

export function LineageSummarySection({ d, reg }) {
  const lineage = d.lineageSummary && typeof d.lineageSummary === "object" && !Array.isArray(d.lineageSummary) ? d.lineageSummary : {};
  const lists = Object.fromEntries(LINEAGE_LISTS.map((item) => [item.key, normalizeLineageList(lineage[item.key])]));
  const warnings = normalizeLineageList(lineage.warnings);
  const totalCount = LINEAGE_LISTS.reduce((total, item) => total + lists[item.key].length, 0);
  const statEntries = normalizeLineageStats(lineage.stats);

  return (
    <Panel
      id="lineage-summary"
      icon="flow"
      title="宽表链路摘要"
      registerRef={reg}
      count={totalCount || "暂无数据"}
      countTone={warnings.length ? "warn" : "info"}
      defaultOpen={totalCount > 0 || warnings.length > 0 || statEntries.length > 0}
    >
      <div className="panel-body">
        <div className="sched-tables">
          {LINEAGE_LISTS.map((item) => (
            <LineageList key={item.key} label={item.label} items={lists[item.key]} />
          ))}
        </div>

        <div style={{ marginTop: 14 }}>
          <div className="subhead" style={{ marginBottom: 7 }}>统计信息</div>
          {statEntries.length ? (
            <div className="metrics">
              {statEntries.map(([key, value]) => (
                <Metric key={key} label={key} value={value} />
              ))}
            </div>
          ) : (
            <div className="sd-empty">暂无数据</div>
          )}
        </div>

        {warnings.length ? (
          <div style={{ marginTop: 14 }}>
            <div className="subhead" style={{ marginBottom: 7 }}><Icon name="alert" size={12} /> 警告</div>
            <div className="flist">
              {warnings.map((warning, index) => (
                <div key={`lineage-warning-${index}`} className="frow warn-row" style={{ height: "auto", padding: "8px 12px", whiteSpace: "normal", overflowWrap: "anywhere" }}>
                  <Badge tone="warn">提示</Badge>
                  <span>{formatLineageItem(warning)}</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </Panel>
  );
}

const SCHED_TABLE_ORDER = ["plan", "seq", "cale", "job"];
const SCHED_TABLE_TITLES = {
  plan: "PLAN 计划清单",
  seq: "SEQ 作业流清单",
  cale: "CALE 日历清单",
  job: "JOB 作业清单",
};

function ScheduleIssueTable({ rows, columns }) {
  if (!rows.length) return null;
  const sortedRows = sortAlertRows(rows);
  return (
    <>
      <div className="subhead" style={{ margin: "12px 0 7px" }}><Icon name="alert" size={12} /> 调度规则告警</div>
      <div className="table-wrap" style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
        <table className="tbl">
          <thead>
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={column.cls || ""}
                  style={column.width || column.minWidth ? { width: column.width, minWidth: column.minWidth } : undefined}
                >
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row, index) => (
              <tr key={index} className={row.level === "err" ? "err-row" : row.level === "warn" ? "warn-row" : ""}>
                <td><Badge mono tone={row.table === "PLAN" ? "accent" : row.table === "SEQ" ? "info" : ""}>{row.table}</Badge></td>
                <td className="rule-cell mono" style={{ fontSize: "var(--fs-xs)" }}>{row.item}</td>
                <td>{row.rule}</td>
                <td className="severity-cell"><Sev level={row.level} /></td>
                <td>{row.msg}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function CycleDependencyList({ findings }) {
  if (!findings.length) return null;
  const graph = toCycleDependencyGraph(findings);
  const pathlessFindings = findings.filter((finding) => !finding.path);
  return (
    <div className="dep-graph cycle-dependency-graph" style={{ marginTop: 14 }}>
      <div className="subhead" style={{ marginBottom: 7 }}><Icon name="flow" size={12} /> 循环依赖</div>
      {graph.nodes.length ? (
        <div className="cycle-lineage-frame">
          <LineageCanvas
            graph={graph}
            ariaLabel="调度作业循环依赖血缘图"
            compact
            initialFit="view"
            showRootControl={false}
            showSelfLoops
          />
        </div>
      ) : null}
      {pathlessFindings.map((finding, index) => (
        <div key={`${finding.msg}-${index}`} className="cycle-dependency-fallback">{finding.msg}</div>
      ))}
    </div>
  );
}

function ScheduleListTables({ tables, issuesByTable, cycleFindings, columns }) {
  const present = SCHED_TABLE_ORDER.filter((key) => (
    tables[key]?.rows?.length
    || issuesByTable[key]?.length
    || (key === "job" && cycleFindings.length)
  ));
  if (!present.length) return null;
  return (
    <div className="sched-tables">
      {present.map((key) => {
        const table = tables[key] || { columns: [], rows: [] };
        const entries = getScheduleTableRows(key, table);
        return (
          <div key={key} className="sched-table-block">
            <div className="subhead" style={{ marginBottom: 7 }}>{table.title || SCHED_TABLE_TITLES[key]}</div>
            {entries.length ? (
              <div className="table-wrap" style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
                <table className="tbl">
                  <thead><tr>{table.columns.map((col) => <th key={col}>{col}</th>)}</tr></thead>
                  <tbody>
                    {entries.map(({ row, state, originalIndex }) => {
                      const cls = state === "new" ? "row-new" : state === "disabled" ? "row-disabled" : "";
                      return (
                        <tr key={originalIndex} className={cls}>
                          {row.map((cell, cellIndex) => <td key={cellIndex} className="mono" style={{ fontSize: "var(--fs-xs)" }}>{cell}</td>)}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : null}
            {key !== "cale" ? <ScheduleIssueTable rows={issuesByTable[key]} columns={columns} /> : null}
            {key === "job" ? <CycleDependencyList findings={cycleFindings} /> : null}
          </div>
        );
      })}
    </div>
  );
}

function ScheduleSection({ d, reg }) {
  const schedule = d.schedule || {};
  const summary = schedule.summary || {};
  const scheduleIssues = getScheduleIssueRows(d);
  const issuesByTable = getScheduleIssuesByTable(d);
  const cycleFindings = getCycleDependencyFindings(d);
  if (!hasScheduleTables(d) && !scheduleIssues.length && !cycleFindings.length) return null;

  const severity = levelOf(scheduleIssues);
  const columns = [
    { key: "table", label: "表" },
    { key: "item", label: "对象", cls: "rule-cell" },
    { key: "rule", label: "规则" },
    { key: "level", label: "级别", cls: "severity-cell", width: 84, minWidth: 84 },
    { key: "msg", label: "说明" },
  ];

  return (
    <Panel
      id="schedule"
      icon="grid"
      title="调度表检查"
      accentHeader
      registerRef={reg}
      count={scheduleIssues.length || "通过"}
      countTone={severity || "ok"}
      defaultOpen
    >
      <div className="panel-body">
        <div className="metrics" style={{ marginBottom: "var(--gap)" }}>
          <Metric label="PLAN" value={summary.plan || 0} />
          <Metric label="SEQ" value={summary.seq || 0} />
          <Metric label="JOB" value={summary.job || 0} />
          <Metric label="循环依赖" value={summary.cycles || 0} tone={summary.cycles ? "err" : "ok"} />
          <Metric label="缺失映射" value={summary.missing || 0} tone={summary.missing ? "warn" : "ok"} />
        </div>
        <ScheduleListTables
          tables={schedule.tables || {}}
          issuesByTable={issuesByTable}
          cycleFindings={cycleFindings}
          columns={columns}
        />
      </div>
    </Panel>
  );
}

export function AiSection({ d, reg }) {
  const ai = d.ai;
  const tone = ai.verdict === "ok" ? "ok" : ai.verdict === "err" ? "err" : "warn";
  return (
    <Panel
      id="ai"
      icon="sparkle"
      title="AI 分析"
      registerRef={reg}
      sub={ai.model}
      right={<Badge tone={tone} icon={tone === "ok" ? "check" : "alert"}>{ai.verdict === "ok" ? "建议合并" : "建议修复"}</Badge>}
    >
      <div className="panel-body ai-body">
        <div className="ai-summary">
          <span className="ai-spark"><Icon name="sparkle" size={15} /></span>
          <p>{ai.summary}</p>
        </div>
        <div className="ai-findings">
          {ai.findings.map((finding, index) => (
            <div key={index} className={`ai-finding ${finding.sev}`}>
              <Sev level={finding.sev} />
              <div className="aif-body">
                <div className="aif-title">{finding.title}</div>
                <div className="aif-text">{finding.body}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}

function aggregateIssues(data) {
  const groups = [
    ["DWS SQL", data.dws],
    ["Hive SQL", data.hive],
    ["配置文件", data.config],
    ["后置脚本", data.sbin],
    ["收卸配置", data.recv],
    ["调度表检查", getScheduleIssueRows(data)],
  ];
  return sortAlertRows(groups.flatMap(([cat, rows]) => rows.map((row) => ({ cat, ...row }))));
}

function IssuesBoard({ d }) {
  const issues = aggregateIssues(d);
  if (!issues.length) {
    return (
      <div className="card" style={{ padding: 20, marginBottom: "var(--gap)" }}>
        <OkState>所有检查项均已通过，未发现需要修复的问题</OkState>
      </div>
    );
  }
  return (
    <div className="card issues-board" style={{ marginBottom: "var(--gap)", overflow: "hidden" }}>
      <div className="ib-head"><Icon name="search" size={14} /> 问题汇总 / 按严重级别排序 <Badge tone="err" mono>{issues.filter((item) => item.level === "err").length} 错误</Badge> <Badge tone="warn" mono>{issues.filter((item) => item.level === "warn").length} 警告</Badge></div>
      <div className="table-wrap">
        <table className="tbl">
          <thead><tr><th className="severity-cell">级别</th><th>分类</th><th>规则</th><th>位置</th><th>说明</th></tr></thead>
          <tbody>
            {issues.map((item, index) => (
              <tr key={index} className={item.level === "err" ? "err-row" : "warn-row"}>
                <td className="severity-cell"><Sev level={item.level} /></td>
                <td><Badge>{item.cat}</Badge></td>
                <td className="rule-cell">{item.rule}</td>
                <td className="mono" style={{ fontSize: "var(--fs-xs)" }}>{item.file || item.item}</td>
                <td>{item.msg}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const CATS = [
  { id: "conflict", label: "trunk 冲突", icon: "conflict", get: (data) => data.conflicts },
  { id: "dws", label: "DWS SQL", icon: "db", get: (data) => data.dws },
  { id: "hive", label: "Hive SQL", icon: "db", get: (data) => data.hive },
  { id: "config", label: "配置文件", icon: "cog", get: (data) => data.config },
  { id: "sbin", label: "后置脚本", icon: "terminal", get: (data) => data.sbin },
  { id: "recv", label: "收卸配置", icon: "download", get: (data) => data.recv },
  { id: "schedule", label: "调度表检查", icon: "grid", get: getScheduleIssueRows },
  { id: "python", label: "Python 脚本", icon: "python", get: getPythonIssueRows },
];

function CategoryBoard({ d, onJump }) {
  return (
    <div className="cat-board">
      {CATS.map((category) => {
        const rows = category.get(d);
        const severity = levelOf(rows) || "ok";
        return (
          <div key={category.id} className={`cat-card ${severity}`} onClick={() => onJump(category.id)}>
            <div className="cc-top">
              <span className="cc-ico"><Icon name={category.icon} size={15} /></span>
              <Dot tone={severity} />
            </div>
            <div className="cc-label">{category.label}</div>
            <div className="cc-stat mono">{rows.length ? `${rows.length} 项` : "通过"}</div>
          </div>
        );
      })}
    </div>
  );
}

export function mergeAuditResults(baseData, apiRows) {
  if (!apiRows?.length) return baseData;
  const grouped = {
    dws: [],
    hive: [],
    python: [],
    sbin: [],
    config: [],
    recv: [],
  };

  apiRows.forEach((row) => {
    const normalized = {
      file: row.file_name,
      rule: row.rule_name,
      level: row.level,
      msg: row.message,
    };
    if (row.category in grouped) {
      grouped[row.category].push(normalized);
    }
  });

  const totalErrors = Object.values(grouped).flat().filter((row) => row.level === "err").length;
  const totalWarnings = Object.values(grouped).flat().filter((row) => row.level === "warn").length;

  return {
    ...baseData,
    task: {
      ...baseData.task,
      errors: totalErrors,
      warnings: totalWarnings,
      status: totalErrors ? "fail" : totalWarnings ? "warn" : "pass",
    },
    ...Object.fromEntries(Object.entries(grouped).map(([key, value]) => [key, value.length ? value : baseData[key]])),
  };
}

export function ResultsPage({ d, aiEnabled, variant, reg, onJump, apiState, onViewLineage, lineageEnabled }) {
  const dismissedScriptIds = useRef(new Set());
  const [openScriptIds, setOpenScriptIds] = useState(() => (
    syncAutoOpenScriptIds(new Set(), d.pyScripts, dismissedScriptIds.current)
  ));
  const mergedData = useMemo(() => mergeAuditResults(d, apiState?.data), [d, apiState?.data]);

  const toggleScript = (scriptId) => {
    setOpenScriptIds((current) => {
      const next = new Set(current);
      if (next.has(scriptId)) {
        next.delete(scriptId);
        dismissedScriptIds.current.add(scriptId);
      } else {
        next.add(scriptId);
        dismissedScriptIds.current.delete(scriptId);
      }
      return next;
    });
  };

  useEffect(() => {
    setOpenScriptIds((current) => (
      syncAutoOpenScriptIds(current, mergedData.pyScripts, dismissedScriptIds.current)
    ));
  }, [mergedData.pyScripts]);

  useEffect(() => {
    const closeAll = (event) => {
      if (event.key === "Escape") {
        setOpenScriptIds((current) => {
          current.forEach((scriptId) => dismissedScriptIds.current.add(scriptId));
          return new Set();
        });
      }
    };
    window.addEventListener("keydown", closeAll);
    return () => window.removeEventListener("keydown", closeAll);
  }, []);

  return (
    <div className="results-page fade-in">
      {apiState?.loading ? <div className="card" style={{ padding: 14, marginBottom: "var(--gap)" }}>正在加载审查结果...</div> : null}
      {apiState?.error ? <div className="card" style={{ padding: 14, marginBottom: "var(--gap)", borderColor: "var(--err)" }}>审查结果接口不可用，请检查任务接口配置。</div> : null}
      <ProgressiveRunPanel d={mergedData} />
      <RunLogs d={mergedData} />
      {variant !== "issues" ? <StatusHeader d={mergedData} /> : null}
      <ModuleProgressBoard d={mergedData} onJump={onJump} />
      {variant === "board" ? (
        <div className="card" style={{ padding: "var(--pad-card)", marginBottom: "var(--gap)" }}>
          <div className="subhead"><Icon name="grid" size={12} /> 检查项概览</div>
          <CategoryBoard d={mergedData} onJump={onJump} />
        </div>
      ) : null}
      {variant === "issues" ? <><StatusHeader d={mergedData} /><IssuesBoard d={mergedData} /></> : null}
      <ChangesSection d={mergedData} reg={reg} />
      <ConflictSection d={mergedData} reg={reg} />
      <CheckSection id="dws" icon="db" title="DWS SQL 检查结果" rows={mergedData.dws} reg={reg} scriptMeta={mergedData.sqlChecks?.dws} />
      <CheckSection id="hive" icon="db" title="Hive SQL 检查结果" rows={mergedData.hive} reg={reg} scriptMeta={mergedData.sqlChecks?.hive} />
      <ConfigCheckSection rows={mergedData.config} files={mergedData.configFiles} reg={reg} />
      <CheckSection id="sbin" icon="terminal" title="后置脚本检查（sbin）" rows={mergedData.sbin} reg={reg} />
      <CheckSection id="recv" icon="download" title="收卸配置检查" rows={mergedData.recv} reg={reg} okMsg="recv_json 配置校验通过" />
      <ScheduleSection d={mergedData} reg={reg} />
      <PyScriptAuditSection d={mergedData} reg={reg} openScriptIds={openScriptIds} onToggle={toggleScript} onViewLineage={onViewLineage} lineageEnabled={lineageEnabled} />
      <AssetIssuesSection d={mergedData} reg={reg} />
      {aiEnabled ? <AiSection d={mergedData} reg={reg} /> : null}
    </div>
  );
}
