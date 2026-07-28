import { Badge, Icon, levelOf, Metric, Panel, Sev } from "../ui";
import { LineageCanvas } from "../lineage/LineageCanvas";
import { toCycleDependencyGraph } from "../lineage/lineageAdapter";
import { getSourceFiles, SourceFileLinks } from "../SourceFileLinks";
import { sortAlertRows } from "../../utils/alertSorting";
import {
  getCycleDependencyFindings,
  getScheduleIssuesByTable,
  getScheduleIssueRows,
  getScheduleTableRows,
  hasScheduleTables,
} from "../../utils/hcytResultPresentation";

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
      <div className="subhead" style={{ margin: "12px 0 7px" }}>
        <Icon name="alert" size={12} /> 调度规则告警
      </div>
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
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={column.cls || ""}
                  style={
                    column.width || column.minWidth
                      ? { width: column.width, minWidth: column.minWidth }
                      : undefined
                  }
                >
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row, index) => (
              <tr
                key={index}
                className={
                  row.level === "err"
                    ? "err-row"
                    : row.level === "warn"
                      ? "warn-row"
                      : ""
                }
              >
                <td>
                  <Badge
                    mono
                    tone={
                      row.table === "PLAN"
                        ? "accent"
                        : row.table === "SEQ"
                          ? "info"
                          : ""
                    }
                  >
                    {row.table}
                  </Badge>
                </td>
                <td
                  className="rule-cell mono"
                  style={{ fontSize: "var(--fs-xs)" }}
                >
                  {row.item}
                </td>
                <td>{row.rule}</td>
                <td className="severity-cell">
                  <Sev level={row.level} />
                </td>
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
      <div className="subhead" style={{ marginBottom: 7 }}>
        <Icon name="flow" size={12} /> 循环依赖
      </div>
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
        <div
          key={`${finding.msg}-${index}`}
          className="cycle-dependency-fallback"
        >
          {finding.msg}
        </div>
      ))}
    </div>
  );
}

function ScheduleListTables({
  tables,
  issuesByTable,
  cycleFindings,
  columns,
  sourceFiles,
}) {
  const present = SCHED_TABLE_ORDER.filter(
    (key) =>
      tables[key]?.rows?.length ||
      issuesByTable[key]?.length ||
      (key === "job" && cycleFindings.length) ||
      sourceFiles.some((file) => file.kind === key),
  );
  if (!present.length) return null;
  return (
    <div className="sched-tables">
      {present.map((key) => {
        const table = tables[key] || { columns: [], rows: [] };
        const entries = getScheduleTableRows(key, table);
        return (
          <div key={key} className="sched-table-block">
            <SourceFileLinks
              files={sourceFiles.filter((file) => file.kind === key)}
              label="原始文件"
            />
            <div className="subhead" style={{ marginBottom: 7 }}>
              {table.title || SCHED_TABLE_TITLES[key]}
            </div>
            {entries.length ? (
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
                      {table.columns.map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {entries.map(({ row, state, originalIndex }) => {
                      const cls =
                        state === "new"
                          ? "row-new"
                          : state === "disabled"
                            ? "row-disabled"
                            : "";
                      return (
                        <tr key={originalIndex} className={cls}>
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
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : null}
            {key !== "cale" ? (
              <ScheduleIssueTable rows={issuesByTable[key]} columns={columns} />
            ) : null}
            {key === "job" ? (
              <CycleDependencyList findings={cycleFindings} />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

export function ScheduleSection({ d, reg }) {
  const schedule = d.schedule || {};
  const summary = schedule.summary || {};
  const scheduleIssues = getScheduleIssueRows(d);
  const issuesByTable = getScheduleIssuesByTable(d);
  const cycleFindings = getCycleDependencyFindings(d);
  const sourceFiles = getSourceFiles(d, "schedule");
  if (
    !hasScheduleTables(d) &&
    !scheduleIssues.length &&
    !cycleFindings.length &&
    !sourceFiles.length
  )
    return null;

  const severity = levelOf(scheduleIssues);
  const columns = [
    { key: "table", label: "表" },
    { key: "item", label: "对象", cls: "rule-cell" },
    { key: "rule", label: "规则" },
    {
      key: "level",
      label: "级别",
      cls: "severity-cell",
      width: 84,
      minWidth: 84,
    },
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
          <Metric
            label="循环依赖"
            value={summary.cycles || 0}
            tone={summary.cycles ? "err" : "ok"}
          />
          <Metric
            label="缺失映射"
            value={summary.missing || 0}
            tone={summary.missing ? "warn" : "ok"}
          />
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
