import { Badge, Dot, Icon, levelOf, OkState, Sev } from "../ui";
import { StatusHero } from "./StatusHero";
import { sortAlertRows } from "../../utils/alertSorting";
import {
  getPythonIssueRows,
  getScheduleIssueRows,
} from "../../utils/hcytResultPresentation";

export function StatusHeader({ d }) {
  const task = d.task;
  return (
    <StatusHero
      data={d}
      workflowIcon="db"
      metrics={[
        { label: "变更文件", value: task.changedFiles, icon: "file" },
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
          label: "冲突",
          value: task.conflicts,
          tone: task.conflicts ? "err" : "ok",
          icon: "conflict",
        },
      ]}
    />
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
  return sortAlertRows(
    groups.flatMap(([cat, rows]) => rows.map((row) => ({ cat, ...row }))),
  );
}

export function IssuesBoard({ d }) {
  const issues = aggregateIssues(d);
  if (!issues.length) {
    return (
      <div className="card" style={{ padding: 20, marginBottom: "var(--gap)" }}>
        <OkState>所有检查项均已通过，未发现需要修复的问题</OkState>
      </div>
    );
  }
  return (
    <div
      className="card issues-board"
      style={{ marginBottom: "var(--gap)", overflow: "hidden" }}
    >
      <div className="ib-head">
        <Icon name="search" size={14} /> 问题汇总 / 按严重级别排序{" "}
        <Badge tone="err" mono>
          {issues.filter((item) => item.level === "err").length} 错误
        </Badge>{" "}
        <Badge tone="warn" mono>
          {issues.filter((item) => item.level === "warn").length} 警告
        </Badge>
      </div>
      <div className="table-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th className="severity-cell">级别</th>
              <th>分类</th>
              <th>规则</th>
              <th>位置</th>
              <th>说明</th>
            </tr>
          </thead>
          <tbody>
            {issues.map((item, index) => (
              <tr
                key={index}
                className={item.level === "err" ? "err-row" : "warn-row"}
              >
                <td className="severity-cell">
                  <Sev level={item.level} />
                </td>
                <td>
                  <Badge>{item.cat}</Badge>
                </td>
                <td className="rule-cell">{item.rule}</td>
                <td className="mono" style={{ fontSize: "var(--fs-xs)" }}>
                  {item.file || item.item}
                </td>
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
  {
    id: "conflict",
    label: "trunk 冲突",
    icon: "conflict",
    get: (data) => data.conflicts,
  },
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
    get: getPythonIssueRows,
  },
];

export function CategoryBoard({ d, onJump }) {
  return (
    <div className="cat-board">
      {CATS.map((category) => {
        const rows = category.get(d);
        const severity = levelOf(rows) || "ok";
        return (
          <div
            key={category.id}
            className={`cat-card ${severity}`}
            onClick={() => onJump(category.id)}
          >
            <div className="cc-top">
              <span className="cc-ico">
                <Icon name={category.icon} size={15} />
              </span>
              <Dot tone={severity} />
            </div>
            <div className="cc-label">{category.label}</div>
            <div className="cc-stat mono">
              {rows.length ? `${rows.length} 项` : "通过"}
            </div>
          </div>
        );
      })}
    </div>
  );
}
