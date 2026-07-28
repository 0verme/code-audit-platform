import { Badge, Icon, Metric } from "../ui";

export const RESULT_STATUS_META = {
  pass: {
    tone: "ok",
    icon: "check",
    label: "审查通过",
    desc: "未发现阻断性问题，可合并",
  },
  fail: {
    tone: "err",
    icon: "x",
    label: "审查未通过",
    desc: "存在需要修复的阻断性问题",
  },
  warn: {
    tone: "warn",
    icon: "alert",
    label: "审查通过（含警告）",
    desc: "存在建议修复的告警项",
  },
  running: {
    tone: "info",
    icon: "clock",
    label: "审查执行中",
    desc: "审查结果正在异步生成，已完成模块会逐步填充到报告中。",
  },
  taskFailed: {
    tone: "err",
    icon: "x",
    label: "任务异常",
    desc: "审查任务异常结束，已完成模块仍可查看。",
  },
};

export function resolveResultStatus(data) {
  const pageStatus = data?.__auditRun?.pageStatus;
  if (pageStatus === "running" || pageStatus === "starting")
    return RESULT_STATUS_META.running;
  if (pageStatus === "failed") return RESULT_STATUS_META.taskFailed;
  return RESULT_STATUS_META[data?.task?.status] || RESULT_STATUS_META.warn;
}

export function StatusHero({
  data,
  workflowIcon,
  description,
  metrics,
  durationLabel = "耗时",
}) {
  const task = data.task;
  const status = resolveResultStatus(data);
  const resolvedDescription =
    typeof description === "function"
      ? description(task, status)
      : description || status.desc;

  return (
    <div className={`status-hero card ${status.tone}`}>
      <div className="sh-main">
        <div className={`sh-badge ${status.tone}`}>
          <Icon name={status.icon} size={26} stroke={2.4} />
        </div>
        <div className="sh-text">
          <div className="sh-title-row">
            <h2 className="sh-title">{status.label}</h2>
            <Badge tone="accent" icon={workflowIcon}>
              {task.workflow}
            </Badge>
          </div>
          <p className="sh-desc">{resolvedDescription}</p>
          <div className="sh-meta mono">
            <span>
              <Icon name="branch" size={12} /> {task.revision}
            </span>
            <span className="sh-sep">/</span>
            <span>{task.author}</span>
            <span className="sh-sep">/</span>
            <span>
              <Icon name="clock" size={12} /> {task.startedAt}
            </span>
            <span className="sh-sep">/</span>
            <span>
              {durationLabel} {task.duration}
            </span>
          </div>
        </div>
      </div>
      <div className="metrics sh-metrics">
        {metrics.map((metric) => (
          <Metric key={metric.label} {...metric} />
        ))}
      </div>
    </div>
  );
}
