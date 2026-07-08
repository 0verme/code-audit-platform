import { useMemo, useState } from "react";
import { AdvancedSettingsPanel } from "../components/advancedSettingsPanel";
import { Dot, Icon } from "../components/ui";
import {
  AUDIT_WORKFLOWS,
  UNKNOWN_WORKFLOW_MESSAGE,
  buildAuditSubmitPayload,
  detectAuditWorkflow,
} from "../config/auditWorkflows";
import {
  UNKNOWN_SOURCE_MESSAGE,
  detectAuditSource,
  isLocalSourceEnabled,
  resolveAuditSourceMeta,
} from "../config/auditSources";
import { APP_EDITION, APP_VERSION } from "../config/appMeta";
import { DEFAULT_RECENT } from "../mock/data";

function mapTaskToRecent(task) {
  const source = resolveAuditSourceMeta(task, { enableLocalSource: true });
  const clientIp = task.client_ip || task.clientIp || "";

  return {
    id: task.id,
    sourceRef: source.sourceRef,
    sourceType: source.sourceType,
    sourceTag: source.tag,
    wf: task.workflow || task.wf,
    rev: task.revision || task.rev,
    status: task.status,
    when: task.started_at || task.when,
    who: clientIp || "",
  };
}

export default function HomePage({
  onSubmit,
  projectsState,
  tasksState,
  onCreateTask,
  dataMode,
}) {
  const [path, setPath] = useState(
    "svn://example.com/repos/branches/demo-hcyt",
  );
  const [ai, setAi] = useState(false);
  const [dbg, setDbg] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const isApiMode = dataMode === "api";
  const localSourceEnabled = isLocalSourceEnabled();
  const detectedSource = detectAuditSource(path, {
    enableLocalSource: localSourceEnabled,
  });
  const detectedWorkflow = detectAuditWorkflow(path);
  const detected = detectedWorkflow?.id || null;
  const canSubmit = Boolean(
    path.trim() && detectedSource.valid && detectedWorkflow,
  );

  const recentList = useMemo(() => {
    if (tasksState.data?.length) {
      return tasksState.data.map(mapTaskToRecent);
    }
    return isApiMode ? [] : DEFAULT_RECENT.map(mapTaskToRecent);
  }, [isApiMode, tasksState.data]);

  async function submit() {
    setSubmitError("");
    if (!detectedSource.valid) {
      setSubmitError(detectedSource.reason || UNKNOWN_SOURCE_MESSAGE);
      return;
    }
    const payload = buildAuditSubmitPayload({
      path,
      ai,
      dbg,
      enableLocalSource: localSourceEnabled,
    });
    if (!payload) {
      setSubmitError(UNKNOWN_WORKFLOW_MESSAGE);
      return;
    }
    if (!isApiMode) {
      onSubmit({ ...payload, taskId: null });
      return;
    }
    const created = await onCreateTask(payload);
    if (created?.error) {
      setSubmitError(`API 模式提交失败：${created.error}`);
      return;
    }
    onSubmit({
      ...payload,
      path: created?.source_ref || created?.sourceRef || payload.path,
      taskId: created?.id ?? null,
      workflow: created?.workflow || payload.workflow,
    });
  }

  return (
    <div className="home-wrap">
      <div className="home-hero fade-in">
        <div className="hero-badge">
          <Dot tone="info" /> {APP_EDITION} · {APP_VERSION}
        </div>
        <h1 className="hero-title">代码提交审查平台</h1>
        <p className="hero-sub">
          输入 SVN / Git
          仓库地址或本地目录路径，平台将自动识别来源类型与审查工作流。
        </p>
      </div>

      <div className="card home-card fade-in">
        <label className="field-label">
          <Icon name="git" size={14} /> 审查路径
        </label>
        <div className="path-input">
          <span className="pi-proto mono">{detectedSource.label}</span>
          <input
            className="pi-field mono"
            value={path}
            spellCheck={false}
            onChange={(event) => setPath(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && submit()}
            placeholder="svn://...、https://...git 或 C:\\path\\to\\workspace"
          />
          {detectedSource.sourceType !== "unknown" ? (
            <span
              className={`pi-detect${detectedSource.valid ? "" : " muted"}`}
            >
              <Dot tone={detectedSource.valid ? "ok" : undefined} />{" "}
              {detectedSource.label}
            </span>
          ) : (
            <span className="pi-detect muted">
              <Dot /> 未识别
            </span>
          )}
        </div>

        <div className="source-summary">
          <span>
            来源类型：<strong>{detectedSource.label}</strong>
          </span>
          <span>
            审查工作流：<strong>{detectedWorkflow?.name || "未识别"}</strong>
          </span>
        </div>

        <div className="route-grid" aria-label="自动识别的审查工作流">
          {AUDIT_WORKFLOWS.map((workflow) => (
            <div
              key={workflow.id}
              className={`route-card readonly${detected === workflow.id ? " active" : " muted"}`}
            >
              <span className="rc-ico" style={{ color: workflow.color }}>
                <Icon name={workflow.icon} size={18} />
              </span>
              <span className="rc-body">
                <span className="rc-name">{workflow.name}</span>
                <span className="rc-kw mono">
                  {workflow.matchKeywords.join(" / ")}
                </span>
                <span className="rc-desc">
                  {workflow.description || workflow.desc}
                </span>
              </span>
              {detected === workflow.id ? (
                <span className="rc-flag">
                  <Icon name="check" size={13} stroke={2.6} />
                </span>
              ) : null}
            </div>
          ))}
        </div>

        {!detectedSource.valid ? (
          <p className="route-hint" style={{ color: "var(--err)" }}>
            <Icon name="info" size={12} /> {detectedSource.reason}
          </p>
        ) : null}
        {!detectedWorkflow ? (
          <p className="route-hint" style={{ color: "var(--err)" }}>
            <Icon name="info" size={12} /> {UNKNOWN_WORKFLOW_MESSAGE}
          </p>
        ) : null}
        {submitError ? (
          <p className="route-hint" style={{ color: "var(--err)" }}>
            {submitError}
          </p>
        ) : null}
        {detectedWorkflow ? (
          <p className="route-hint">
            <Icon name="info" size={12} /> 已自动识别工作流：
            {detectedWorkflow.name}
          </p>
        ) : null}

        {isApiMode && projectsState.loading ? (
          <p className="route-hint">正在加载后端项目列表...</p>
        ) : null}
        {isApiMode && projectsState.error ? (
          <p className="route-hint" style={{ color: "var(--err)" }}>
            项目列表接口不可用，请检查 API 服务或 `VITE_API_BASE_URL`。
          </p>
        ) : null}
        {projectsState.data?.length ? (
          <div className="chips" style={{ marginBottom: 12 }}>
            {projectsState.data.map((project) => (
              <span key={project.id} className="chip src">
                {project.name}
              </span>
            ))}
          </div>
        ) : null}

        <div className="divline" />

        <AdvancedSettingsPanel
          ai={ai}
          dbg={dbg}
          onAiChange={setAi}
          onDbgChange={setDbg}
        />

        <div className="home-actions">
          <span className="ha-meta mono">
            {detectedWorkflow ? detectedWorkflow.name : "未识别工作流"}
          </span>
          <button
            className="btn primary lg"
            onClick={submit}
            disabled={!canSubmit}
          >
            <Icon name="play" size={15} stroke={2.2} /> 提交审查
          </button>
        </div>
      </div>

      <div className="recent-block fade-in">
        <div className="subhead">
          <Icon name="clock" size={12} /> 最近审查
        </div>
        {tasksState.loading ? (
          <div className="card recent-list">正在加载任务列表...</div>
        ) : null}
        <div className="card recent-list">
          {recentList.length ? (
            <div className="recent-head">
              <span />
              <span>版本</span>
              <span>审查来源</span>
              <span>审查类型</span>
              <span>IP</span>
              <span>时间</span>
            </div>
          ) : null}
          {recentList.length ? (
            recentList.map((item, index) => {
              const workflow =
                AUDIT_WORKFLOWS.find((entry) => entry.id === item.wf) ||
                AUDIT_WORKFLOWS[0];
              const tone =
                item.status === "pass"
                  ? "ok"
                  : item.status === "fail"
                    ? "err"
                    : "warn";
              return (
                <div
                  key={`${item.rev}-${index}`}
                  className="recent-row"
                  onClick={() =>
                    onSubmit({
                      path: item.sourceRef,
                      ai: false,
                      dbg: false,
                      workflow: item.wf,
                      type: item.wf,
                      taskId: item.id ?? null,
                    })
                  }
                >
                  <Dot tone={tone} />
                  <span className="rr-rev mono">{item.rev}</span>
                  <span className="rr-source mono">
                    <span className="rr-tag">{item.sourceTag}</span>
                    {item.sourceRef}
                  </span>
                  <span className="rr-wf">
                    <Icon
                      name={workflow.icon}
                      size={12}
                      style={{ color: workflow.color }}
                    />{" "}
                    {workflow.name}
                  </span>
                  <span className="rr-who">{item.who}</span>
                  <span className="rr-when">{item.when}</span>
                </div>
              );
            })
          ) : (
            <div className="recent-row">暂无审查任务</div>
          )}
        </div>
        {isApiMode && tasksState.error ? (
          <p className="route-hint" style={{ color: "var(--err)" }}>
            任务接口不可用，无法加载真实任务列表。
          </p>
        ) : null}
      </div>
    </div>
  );
}
