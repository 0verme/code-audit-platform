import { useMemo, useState } from "react";
import { Dot, Icon } from "../components/ui";
import {
  AUDIT_WORKFLOWS,
  UNKNOWN_WORKFLOW_MESSAGE,
  buildAuditSubmitPayload,
  detectAuditWorkflow,
} from "../config/auditWorkflows";
import { DEFAULT_RECENT } from "../mock/data";

function Toggle({ on, onChange, label, desc, icon }) {
  return (
    <div className="row-toggle" onClick={() => onChange(!on)}>
      <span className="rt-ico"><Icon name={icon} size={16} /></span>
      <span className="rt-text">
        <span className="rt-label">{label}</span>
        <span className="rt-desc">{desc}</span>
      </span>
      <span className={`switch${on ? " on" : ""}`}><span className="knob" /></span>
    </div>
  );
}

function mapTaskToRecent(task) {
  return {
    id: task.id,
    repo: task.repo,
    wf: task.workflow,
    rev: task.revision,
    status: task.status,
    when: task.started_at,
    who: task.author,
  };
}

export default function HomePage({ onSubmit, projectsState, tasksState, onCreateTask, dataMode, apiBaseUrl }) {
  const [sourceType, setSourceType] = useState("svn");
  const [path, setPath] = useState("svn://example.com/repos/branches/demo-hcyt");
  const [ai, setAi] = useState(false);
  const [dbg, setDbg] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const isApiMode = dataMode === "api";

  const detectedWorkflow = detectAuditWorkflow(path);
  const detected = detectedWorkflow?.id || null;
  const canSubmit = Boolean(path.trim() && detectedWorkflow);
  const recentList = useMemo(() => {
    if (tasksState.data?.length) {
      return tasksState.data.map(mapTaskToRecent);
    }
    return isApiMode ? [] : DEFAULT_RECENT;
  }, [isApiMode, tasksState.data]);

  async function submit() {
    setSubmitError("");
    const payload = buildAuditSubmitPayload({ path, sourceType, ai, dbg });
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
    onSubmit({ ...payload, taskId: created?.id ?? null, workflow: created?.workflow || payload.workflow });
  }

  return (
    <div className="home-wrap">
      <div className="home-hero fade-in">
        <div className="hero-badge"><Dot tone="ok" pulse /> 审查引擎在线 / v3.4.2</div>
        <h1 className="hero-title">代码提交审查平台</h1>
        <p className="hero-sub">输入 SVN / Git 仓库路径，平台将自动检测、分类并按规则集进行多维静态审查。</p>
      </div>

      <div className="card home-card fade-in">
        <label className="field-label"><Icon name={sourceType === "local" ? "folder" : "git"} size={14} /> 审计来源</label>
        <div className="chips" style={{ marginBottom: 12 }}>
          <button
            type="button"
            className={`chip src${sourceType === "svn" ? " active" : ""}`}
            onClick={() => {
              setSourceType("svn");
              setPath("svn://example.com/repos/branches/demo-hcyt");
            }}
          >
            SVN
          </button>
          <button
            type="button"
            className={`chip src${sourceType === "local" ? " active" : ""}`}
            onClick={() => {
              setSourceType("local");
              setPath("C:\\path\\to\\local-hcyt-workspace");
            }}
          >
            本地目录
          </button>
        </div>
        <label className="field-label"><Icon name="git" size={14} /> 仓库路径</label>
        <div className="path-input">
          <span className="pi-proto mono">{sourceType === "local" ? "dir" : (path.startsWith("http") ? "https" : "svn")}</span>
          <input
            className="pi-field mono"
            value={path}
            spellCheck={false}
            onChange={(event) => setPath(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && submit()}
            placeholder="svn://... 或 https://..."
          />
          {detected ? <span className="pi-detect"><Dot tone="ok" /> 已识别</span> : <span className="pi-detect muted"><Dot /> 待识别</span>}
        </div>

        <div className="route-grid" aria-label="自动识别的审查工作流">
          {AUDIT_WORKFLOWS.map((workflow) => (
            <div
              key={workflow.id}
              className={`route-card readonly${detected === workflow.id ? " active" : " muted"}`}
            >
              <span className="rc-ico" style={{ color: workflow.color }}><Icon name={workflow.icon} size={18} /></span>
              <span className="rc-body">
                <span className="rc-name">{workflow.name}</span>
                <span className="rc-kw mono">{workflow.matchKeywords.join(" / ")}</span>
              </span>
              {detected === workflow.id ? <span className="rc-flag"><Icon name="check" size={13} stroke={2.6} /></span> : null}
            </div>
          ))}
        </div>
        {!detectedWorkflow ? <p className="route-hint" style={{ color: "var(--err)" }}><Icon name="info" size={12} /> {UNKNOWN_WORKFLOW_MESSAGE}</p> : null}
        {submitError ? <p className="route-hint" style={{ color: "var(--err)" }}>{submitError}</p> : null}
        {detectedWorkflow ? <p className="route-hint"><Icon name="info" size={12} /> 已自动识别为：{detectedWorkflow.name}</p> : null}

        <p className="route-hint"><Icon name="info" size={12} /> 当前任务接口模式：{isApiMode ? `API（${apiBaseUrl}）` : "mock（本地演示数据）"}</p>
        {isApiMode && projectsState.loading ? <p className="route-hint">正在加载后端项目列表...</p> : null}
        {isApiMode && projectsState.error ? <p className="route-hint" style={{ color: "var(--err)" }}>项目列表接口不可用，请检查 API 服务或 VITE_API_BASE_URL。</p> : null}
        {projectsState.data?.length ? (
          <div className="chips" style={{ marginBottom: 12 }}>
            {projectsState.data.map((project) => (
              <span key={project.id} className="chip src">{project.name}</span>
            ))}
          </div>
        ) : null}

        <div className="divline" />

        <div className="toggles">
          <Toggle on={ai} onChange={setAi} icon="sparkle" label="接入本地 AI 大模型" desc="启用后追加 AI 语义分析与修复建议（默认关闭）" />
          <Toggle on={dbg} onChange={setDbg} icon="terminal" label="调试日志" desc="输出检测、分类与规则执行的详细日志（默认关闭）" />
        </div>

        <div className="home-actions">
          <span className="ha-meta mono">{detectedWorkflow ? detectedWorkflow.name : "未识别工作流"}</span>
          <button className="btn primary lg" onClick={submit} disabled={!canSubmit}>
            <Icon name="play" size={15} stroke={2.2} /> 提交审查
          </button>
        </div>
      </div>

      <div className="recent-block fade-in">
        <div className="subhead"><Icon name="clock" size={12} /> 最近审查</div>
        {tasksState.loading ? <div className="card recent-list">正在加载任务列表...</div> : null}
        <div className="card recent-list">
          {recentList.length ? recentList.map((item, index) => {
            const workflow = AUDIT_WORKFLOWS.find((entry) => entry.id === item.wf) || AUDIT_WORKFLOWS[0];
            const tone = item.status === "pass" ? "ok" : item.status === "fail" ? "err" : "warn";
            return (
              <div key={`${item.rev}-${index}`} className="recent-row" onClick={() => onSubmit({ path: item.repo, ai: false, dbg: false, workflow: item.wf, type: item.wf, taskId: item.id ?? null })}>
                <Dot tone={tone} />
                <span className="rr-rev mono">{item.rev}</span>
                <span className="rr-repo mono">{item.repo}</span>
                <span className="rr-wf"><Icon name={workflow.icon} size={12} style={{ color: workflow.color }} /> {workflow.name}</span>
                <span className="rr-who">{item.who}</span>
                <span className="rr-when">{item.when}</span>
              </div>
            );
          }) : <div className="recent-row">暂无审查任务</div>}
        </div>
        {isApiMode && tasksState.error ? <p className="route-hint" style={{ color: "var(--err)" }}>任务接口不可用，无法加载真实任务列表。</p> : null}
      </div>
    </div>
  );
}
