import { Fragment, useMemo, useState } from "react";
import { Badge, Dot, Icon, levelOf, OkState, Panel, Sev, ViolationTable } from "../components/ui";
import { LineageCanvas } from "../components/lineage/LineageCanvas";
import { toCycleDependencyGraph } from "../components/lineage/lineageAdapter";
import { ChangeFilesSection } from "../components/results/ChangeFilesSection";
import { ModuleProgressBoard, ProgressiveRunPanel, RunLogs } from "../components/results/HcytRunProgress";
import { AiSection, AssetIssuesSection } from "../components/results/SharedResultSections";
import { StatusHero } from "../components/results/StatusHero";
import { getSourceFiles, SourceFileLinks } from "../components/SourceFileLinks";
import { useAutoOpenAccordion } from "../hooks/useAutoOpenAccordion";
import { getScriptElementId, getScriptKey, scriptAudit } from "../utils/scriptAuditPresentation";
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

function StatusHeader({ d }) {
  const task = d.task;
  return (
    <StatusHero
      data={d}
      workflowIcon="db"
      metrics={[
        { label: "变更文件", value: task.changedFiles, icon: "file" },
        { label: "检查项", value: task.checks, icon: "layers" },
        { label: "错误", value: task.errors, tone: task.errors ? "err" : "ok", icon: "x" },
        { label: "警告", value: task.warnings, tone: task.warnings ? "warn" : "ok", icon: "alert" },
        { label: "冲突", value: task.conflicts, tone: task.conflicts ? "err" : "ok", icon: "conflict" },
      ]}
    />
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
            {d.conflicts.map((conflict) => {
              const source = d.changes.find((change) => change.path === conflict.path)
                || (d.sourceFiles || []).find((file) => file.path === conflict.path);
              return (
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
                {source?.downloadUrl ? (
                  <a className="dl-link" href={source.downloadUrl} target="_blank" rel="noreferrer">
                    <Icon name="download" size={12} /> 下载
                  </a>
                ) : null}
              </div>
              );
            })}
          </div>
        ) : <OkState>未检测到与 trunk 主干的重叠冲突</OkState>}
      </div>
    </Panel>
  );
}

function CheckSection({ id, icon, title, rows = [], reg, okMsg, scriptMeta, sourceFiles = [] }) {
  if (!rows.length && !scriptMeta?.script && !sourceFiles.length) return null;

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
      <SourceFileLinks files={sourceFiles} />
      <div className={rows.length ? "panel-body flush" : "panel-body"}>
        {rows.length ? <ViolationTable rows={rows} /> : <OkState>{okMsg || "未发现违规项"}</OkState>}
      </div>
    </Panel>
  );
}

function ConfigFilesDetail({ files, sourceFiles, detailId }) {
  return (
    <tr className="config-detail-row">
      <td colSpan={4}>
        <section id={detailId} className="config-detail fade-in" role="region" aria-label="SCHEMA_CONFIG 详情">
          {files.length ? files.map((file, fileIndex) => (
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
          )) : (
            <div className="sd-empty">
              已识别到 {sourceFiles.length} 个配置文件，但暂未生成可展示的解析明细；请等待配置检查完成后重试。
            </div>
          )}
        </section>
      </td>
    </tr>
  );
}

function ConfigCheckSection({ rows = [], files = [], sourceFiles = [], reg }) {
  const [openRowIndex, setOpenRowIndex] = useState(null);
  if (!rows.length && !files.length && !sourceFiles.length) return null;

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
      <SourceFileLinks files={sourceFiles} label="配置文件" />
      <div className="panel-body flush">
        <div className="table-wrap">
          <table className="tbl config-check-table">
            <thead>
              <tr><th>文件</th><th>规则</th><th className="severity-cell">级别</th><th>说明</th></tr>
            </thead>
            <tbody>
              {displayRows.map((row, rowIndex) => {
                const isSchemaConfig = String(row.file || "").toUpperCase() === "SCHEMA_CONFIG";
                const canExpand = isSchemaConfig && (files.length > 0 || sourceFiles.length > 0);
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
                    {isOpen ? <ConfigFilesDetail files={files} sourceFiles={sourceFiles} detailId={detailId} /> : null}
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

function ScheduleListTables({ tables, issuesByTable, cycleFindings, columns, sourceFiles }) {
  const present = SCHED_TABLE_ORDER.filter((key) => (
    tables[key]?.rows?.length
    || issuesByTable[key]?.length
    || (key === "job" && cycleFindings.length)
    || sourceFiles.some((file) => file.kind === key)
  ));
  if (!present.length) return null;
  return (
    <div className="sched-tables">
      {present.map((key) => {
        const table = tables[key] || { columns: [], rows: [] };
        const entries = getScheduleTableRows(key, table);
        return (
          <div key={key} className="sched-table-block">
            <SourceFileLinks files={sourceFiles.filter((file) => file.kind === key)} label="原始文件" />
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
  const sourceFiles = getSourceFiles(d, "schedule");
  if (!hasScheduleTables(d) && !scheduleIssues.length && !cycleFindings.length && !sourceFiles.length) return null;

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
          sourceFiles={sourceFiles}
        />
      </div>
    </Panel>
  );
}

function OtherSourceFilesSection({ d, reg }) {
  const files = getSourceFiles(d, "other-files");
  if (!files.length) return null;
  return (
    <Panel id="other-files" icon="file" title="其他审计文件" registerRef={reg} count={files.length} countTone="info">
      <SourceFileLinks files={files} label="审计输入" />
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

function mergeAuditResults(baseData, apiRows) {
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

const hasScriptFinding = (script) => {
  const audit = scriptAudit(script);
  return Boolean(audit.err || audit.warn);
};

export function ResultsPage({ d, aiEnabled, variant, reg, onJump, apiState, onViewLineage, lineageEnabled, scriptJumpRequest }) {
  const mergedData = useMemo(() => mergeAuditResults(d, apiState?.data), [d, apiState?.data]);
  const { openIds: openScriptIds, toggle: toggleScript } = useAutoOpenAccordion({
    items: mergedData.pyScripts,
    getKey: getScriptKey,
    isActionable: hasScriptFinding,
    jumpRequest: scriptJumpRequest,
    getElementId: getScriptElementId,
  });

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
      <ChangeFilesSection changes={mergedData.changes} registerRef={reg} showSummary showFileDiff />
      <ConflictSection d={mergedData} reg={reg} />
      <CheckSection id="dws" icon="db" title="DWS SQL 检查结果" rows={mergedData.dws} reg={reg} scriptMeta={mergedData.sqlChecks?.dws} />
      <CheckSection id="hive" icon="db" title="Hive SQL 检查结果" rows={mergedData.hive} reg={reg} scriptMeta={mergedData.sqlChecks?.hive} />
      <ConfigCheckSection rows={mergedData.config} files={mergedData.configFiles} sourceFiles={getSourceFiles(mergedData, "config")} reg={reg} />
      <CheckSection id="sbin" icon="terminal" title="后置脚本检查（sbin）" rows={mergedData.sbin} reg={reg} sourceFiles={getSourceFiles(mergedData, "sbin")} />
      <CheckSection id="recv" icon="download" title="收卸配置检查" rows={mergedData.recv} reg={reg} okMsg="recv_json 配置校验通过" sourceFiles={getSourceFiles(mergedData, "recv")} />
      <ScheduleSection d={mergedData} reg={reg} />
      <PyScriptAuditSection d={mergedData} reg={reg} openScriptIds={openScriptIds} onToggle={toggleScript} onViewLineage={onViewLineage} lineageEnabled={lineageEnabled} />
      <OtherSourceFilesSection d={mergedData} reg={reg} />
      <AssetIssuesSection d={mergedData} reg={reg} />
      {aiEnabled ? <AiSection d={mergedData} reg={reg} /> : null}
    </div>
  );
}
