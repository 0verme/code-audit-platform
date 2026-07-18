import { useMemo, useRef, useState } from "react";
import { AdvancedSettingsPanel } from "../components/advancedSettingsPanel";
import { RecentAuditHistoryPanel } from "../components/RecentAuditHistoryPanel";
import { Dot, Icon } from "../components/ui";
import {
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
import { getHomePathFeedbackState } from "../utils/homePathFeedback";

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
  submitting = false,
}) {
  const [path, setPath] = useState(
    "",
  );
  const [ai, setAi] = useState(false);
  const [dbg, setDbg] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [hasValidatedPath, setHasValidatedPath] = useState(false);
  const [submitPending, setSubmitPending] = useState(false);
  const submitLockRef = useRef(false);
  const isApiMode = dataMode === "api";
  const localSourceEnabled = isLocalSourceEnabled();
  const detectedSource = detectAuditSource(path, {
    enableLocalSource: localSourceEnabled,
  });
  const detectedWorkflow = detectAuditWorkflow(path);
  const detected = detectedWorkflow?.id || null;
  const pathFeedback = getHomePathFeedbackState({
    path,
    detectedSource,
    detectedWorkflow,
    hasValidated: hasValidatedPath,
    submitError,
  });
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
    if (submitLockRef.current) return;
    setSubmitError("");
    setHasValidatedPath(true);
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
    submitLockRef.current = true;
    setSubmitPending(true);
    try {
      const created = await onCreateTask(payload);
      if (created?.errorCode === "local_source_disabled") {
        setSubmitError("后端未启用本地目录审计，请联系部署管理员配置后端授权。");
        return;
      }
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
    } finally {
      submitLockRef.current = false;
      setSubmitPending(false);
    }
  }

  function handleRecentSelect(item) {
    onSubmit({
      path: item.sourceRef,
      ai: false,
      dbg: false,
      workflow: item.wf,
      type: item.wf,
      taskId: item.id ?? null,
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
          输入 SVN 仓库地址或本地目录路径，平台将自动识别来源类型与审查工作流。
        </p>
      </div>

      <div className="card home-card fade-in">
        <label className="field-label">
          <Icon name="git" size={14} /> 审查路径
        </label>
        <div className="path-input">
          {pathFeedback.showInputDetection ? (
            <span className="pi-proto mono">{detectedSource.label}</span>
          ) : null}
          <input
            className="pi-field mono"
            value={path}
            spellCheck={false}
            onChange={(event) => setPath(event.target.value)}
            onBlur={() => setHasValidatedPath(true)}
            onKeyDown={(event) => event.key === "Enter" && submit()}
            placeholder="svn://svnj.app.cz/hcyt 或 fine-report"
          />
          {pathFeedback.showInputDetection && detectedSource.sourceType !== "unknown" ? (
            <span
              className={`pi-detect${detectedSource.valid ? "" : " muted"}`}
            >
              <Dot tone={detectedSource.valid ? "ok" : undefined} />{" "}
              {detectedSource.label}
            </span>
          ) : pathFeedback.showInputDetection ? (
            <span className="pi-detect muted">
              <Dot /> 未识别
            </span>
          ) : null}
        </div>

        {pathFeedback.showRouteCard ? (
          <div className="route-grid" aria-label="自动识别的审查工作流">
            {[detectedWorkflow].map((workflow) => (
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
        ) : null}

        {pathFeedback.showSourceError ? (
          <p className="route-hint" style={{ color: "var(--err)" }}>
            <Icon name="info" size={12} /> {detectedSource.reason}
          </p>
        ) : null}
        {pathFeedback.showWorkflowError ? (
          <p className="route-hint" style={{ color: "var(--err)" }}>
            <Icon name="info" size={12} /> {UNKNOWN_WORKFLOW_MESSAGE}
          </p>
        ) : null}
        {pathFeedback.showSubmitError ? (
          <p className="route-hint" style={{ color: "var(--err)" }}>
            {submitError}
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
          <div className="chips home-project-chips">
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
          <button
            className="btn primary lg"
            onClick={submit}
            disabled={!canSubmit || submitting || submitPending}
          >
            <Icon name="play" size={15} stroke={2.2} /> {submitting || submitPending ? "提交中..." : "提交审查"}
          </button>
        </div>
      </div>

      <div className="recent-block fade-in">
        <RecentAuditHistoryPanel
          items={recentList}
          loading={tasksState.loading}
          error={isApiMode ? tasksState.error : null}
          onSelect={handleRecentSelect}
        />
      </div>
    </div>
  );
}
