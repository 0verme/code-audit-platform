import { Badge, Icon } from "../ui";

export const MODULE_TASKS = [
  {
    key: "source_load",
    section: "changes",
    label: "读取工作区 / SVN",
    icon: "download",
  },
  { key: "classify_files", section: "changes", label: "变更文件", icon: "git" },
  {
    key: "trunk_conflicts",
    section: "conflict",
    label: "trunk 冲突",
    icon: "conflict",
  },
  { key: "dws_sql", section: "dws", label: "DWS SQL", icon: "db" },
  { key: "hive_sql", section: "hive", label: "Hive SQL", icon: "db" },
  { key: "config_files", section: "config", label: "配置文件", icon: "cog" },
  { key: "post_scripts", section: "sbin", label: "后置脚本", icon: "terminal" },
  { key: "recv_config", section: "recv", label: "收卸配置", icon: "download" },
  { key: "schedule", section: "schedule", label: "调度表检查", icon: "grid" },
  {
    key: "python_scripts",
    section: "python",
    label: "Python 脚本",
    icon: "python",
  },
  {
    key: "lineage",
    section: "lineage-summary",
    label: "依赖链分析",
    icon: "flow",
  },
  { key: "summary", section: "overview", label: "保存审查报告", icon: "check" },
];

const TASK_STATUS_META = {
  queued: { tone: "", label: "排队中" },
  running: { tone: "info", label: "执行中" },
  success: { tone: "ok", label: "已完成" },
  skipped: { tone: "warn", label: "已跳过" },
  failed: { tone: "err", label: "检查异常" },
};

export const NUPS_MODULE_TASKS = [
  {
    key: "source_load",
    section: "changes",
    label: "读取工作区 / SVN",
    icon: "download",
  },
  { key: "classify_files", section: "changes", label: "变更文件", icon: "git" },
  {
    key: "trunk_conflicts",
    section: "conflict",
    label: "trunk 冲突",
    icon: "conflict",
  },
  { key: "dws_sql", section: "nups-sql", label: "NUPS SQL", icon: "db" },
  {
    key: "python_scripts",
    section: "nups-py",
    label: "NUPS 加工程序",
    icon: "python",
  },
  { key: "summary", section: "overview", label: "保存审查报告", icon: "check" },
];

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

export function ProgressiveRunPanel({ d, moduleTasks = MODULE_TASKS }) {
  const run = d.__auditRun;
  if (!run || run.finalReportReady) return null;
  const tasks = run.tasks || {};
  const taskValues = moduleTasks
    .map((module) => tasks[module.key])
    .filter(Boolean);
  const completed = taskValues.filter((task) =>
    ["success", "skipped", "failed"].includes(task.status),
  ).length;
  const total = moduleTasks.length;
  const percent = Math.max(
    0,
    Math.min(100, Number(run.progress?.percent || 0)),
  );
  const failed =
    run.progress?.failed ??
    taskValues.filter((task) => task.status === "failed").length;
  const skipped =
    run.progress?.skipped ??
    taskValues.filter((task) => task.status === "skipped").length;
  const elapsed = elapsedSince(
    run.statusPayload?.startedAt ||
      run.statusPayload?.task?.started_at ||
      d.task.startedAt,
  );

  return (
    <div
      className={`card progressive-run ${run.pageStatus === "failed" ? "failed" : ""}`}
    >
      <div className="progressive-main">
        <div>
          <div className="section-title">
            <Icon
              name={run.pageStatus === "failed" ? "x" : "clock"}
              size={16}
            />{" "}
            {run.pageStatus === "failed" ? "任务异常" : "审查执行中"}
          </div>
          <div className="progressive-sub">
            当前模块：{run.currentModule || "等待调度"} · 已完成 {completed}/
            {total} · 耗时 {elapsed}
          </div>
        </div>
        <div className="progressive-counts">
          <Badge tone={d.task.errors ? "err" : "ok"} mono>
            错误 {d.task.errors || 0}
          </Badge>
          <Badge tone={d.task.warnings ? "warn" : "ok"} mono>
            警告 {d.task.warnings || 0}
          </Badge>
          <Badge tone={d.task.conflicts ? "err" : "ok"} mono>
            冲突 {d.task.conflicts || 0}
          </Badge>
          {failed ? (
            <Badge tone="err" mono>
              异常 {failed}
            </Badge>
          ) : null}
          {skipped ? (
            <Badge tone="warn" mono>
              跳过 {skipped}
            </Badge>
          ) : null}
        </div>
      </div>
      <div className="real-progress" aria-label="审查进度">
        <span style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

export function ModuleProgressBoard({ d, onJump, modules = MODULE_TASKS }) {
  const run = d.__auditRun;
  if (!run) return null;
  const tasks = run.tasks || {};

  return (
    <div className="card module-progress-board">
      <div className="subhead">
        <Icon name="grid" size={12} /> 模块执行状态
      </div>
      <div className="module-progress-grid">
        {modules.map((module) => {
          const state = tasks[module.key] || {};
          const status = state.status || "queued";
          const meta = TASK_STATUS_META[status] || TASK_STATUS_META.queued;
          const duration = formatDurationMs(state.durationMs);
          return (
            <button
              key={module.key}
              className={`module-progress-card ${status}`}
              onClick={() => onJump?.(module.section)}
            >
              <span className="mp-icon">
                <Icon name={module.icon} size={14} />
              </span>
              <span className="mp-body">
                <span className="mp-title">{module.label}</span>
                <span className="mp-meta">
                  <Badge tone={meta.tone} mono>
                    {meta.label}
                  </Badge>
                  {duration ? <span>{duration}</span> : null}
                  {status === "running" && state.startedAt ? (
                    <span>当前 {elapsedSince(state.startedAt)}</span>
                  ) : null}
                  {Number(state.durationMs) > 10000 ? (
                    <span className="slow-hint">耗时较长</span>
                  ) : null}
                </span>
                {state.error ? (
                  <span className="mp-error">{state.error}</span>
                ) : null}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function RunLogs({ d }) {
  const logs = d.__auditRun?.logs || d.logs || [];
  if (!logs.length) return null;
  return (
    <details className="card run-logs">
      <summary>
        <Icon name="terminal" size={13} /> 查看执行日志{" "}
        <Badge mono>{logs.length}</Badge>
      </summary>
      <pre className="mono">
        {logs
          .slice(-80)
          .map(
            (entry) =>
              `[${entry.ts || "-"}] ${entry.level || "INFO"} ${entry.msg || entry.message || ""}`,
          )
          .join("\n")}
      </pre>
    </details>
  );
}
