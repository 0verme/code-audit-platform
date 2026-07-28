import { Icon } from "../ui";

export function RunningView({ task }) {
  const progress = task?.progress ?? 0;
  const step = task?.step || "排队中";
  const recentLogs = (task?.logs || []).slice(-12);
  return (
    <div className="card fade-in task-state-card">
      <div
        className="section-title"
        style={{ display: "flex", alignItems: "center", gap: 8 }}
      >
        <Icon name="clock" size={16} /> 审查任务执行中
      </div>
      <p className="muted" style={{ margin: "10px 0 6px" }}>
        当前步骤：{step}
      </p>
      <div
        style={{
          height: 8,
          borderRadius: 4,
          background: "var(--border)",
          overflow: "hidden",
          margin: "10px 0 16px",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${progress}%`,
            background: "var(--accent)",
            transition: "width .4s",
          }}
        />
      </div>
      {recentLogs.length ? (
        <pre
          className="mono"
          style={{
            fontSize: "var(--fs-xs)",
            color: "var(--text-2)",
            whiteSpace: "pre-wrap",
            margin: 0,
          }}
        >
          {recentLogs.map((entry) => `[${entry.ts}] ${entry.msg}`).join("\n")}
        </pre>
      ) : null}
    </div>
  );
}

export function FailedView({ task, onBack }) {
  const recentLogs = (task?.logs || []).slice(-20);
  return (
    <div
      className="card fade-in task-state-card"
      style={{ borderColor: "var(--err)" }}
    >
      <div
        className="section-title"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          color: "var(--err-fg)",
        }}
      >
        <Icon name="x" size={16} /> 审查任务执行失败
      </div>
      <p className="muted" style={{ margin: "10px 0" }}>
        {task?.error || "任务异常结束，未生成报告。"}
      </p>
      {recentLogs.length ? (
        <pre
          className="mono"
          style={{
            fontSize: "var(--fs-xs)",
            color: "var(--text-2)",
            whiteSpace: "pre-wrap",
            margin: "0 0 14px",
          }}
        >
          {recentLogs
            .map((entry) => `[${entry.ts}] ${entry.level} ${entry.msg}`)
            .join("\n")}
        </pre>
      ) : null}
      <button className="btn primary" onClick={onBack}>
        <Icon
          name="chevron"
          size={14}
          style={{ transform: "rotate(180deg)" }}
        />{" "}
        返回首页
      </button>
    </div>
  );
}

export function ApiErrorView({ error, onBack }) {
  return (
    <div
      className="card fade-in task-state-card"
      style={{ borderColor: "var(--err)" }}
    >
      <div
        className="section-title"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          color: "var(--err-fg)",
        }}
      >
        <Icon name="x" size={16} /> 任务接口不可用
      </div>
      <p className="muted" style={{ margin: "10px 0 14px" }}>
        API 模式不会自动降级为 mock。请检查后端服务、网络连接或
        VITE_API_BASE_URL。
      </p>
      {error ? (
        <pre
          className="mono"
          style={{
            fontSize: "var(--fs-xs)",
            color: "var(--err-fg)",
            whiteSpace: "pre-wrap",
            margin: "0 0 14px",
          }}
        >
          {error.message || String(error)}
        </pre>
      ) : null}
      <button className="btn primary" onClick={onBack}>
        <Icon
          name="chevron"
          size={14}
          style={{ transform: "rotate(180deg)" }}
        />{" "}
        返回首页
      </button>
    </div>
  );
}

export function PageFallback() {
  return (
    <div className="card" style={{ padding: 24 }}>
      <div className="section-title">Loading...</div>
      <p className="muted" style={{ margin: "8px 0 0" }}>
        Page resources are loading.
      </p>
    </div>
  );
}
