import { useMemo, useState } from "react";
import { Dot, Icon } from "../components/ui";
import { DEFAULT_RECENT, WORKFLOWS, detectWorkflow } from "../mock/data";

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
    repo: task.repo,
    wf: task.workflow,
    rev: task.revision,
    status: task.status,
    when: task.started_at,
    who: task.author,
  };
}

export default function HomePage({ onSubmit, projectsState, tasksState, onCreateTask }) {
  const [path, setPath] = useState("svn://10.18.32.7/datawh/branches/2026Q2/hcyt");
  const [ai, setAi] = useState(false);
  const [dbg, setDbg] = useState(false);

  const detected = detectWorkflow(path);
  const recentList = useMemo(() => {
    if (tasksState.data?.length) {
      return tasksState.data.map(mapTaskToRecent);
    }
    return DEFAULT_RECENT;
  }, [tasksState.data]);

  async function submit() {
    if (!path.trim()) return;
    const payload = { path: path.trim(), ai, dbg, workflow: detected || "hcyt" };
    await onCreateTask(payload);
    onSubmit(payload);
  }

  return (
    <div className="home-wrap">
      <div className="home-hero fade-in">
        <div className="hero-badge"><Dot tone="ok" pulse /> 审查引擎在线 / v3.4.2</div>
        <h1 className="hero-title">代码提交审查平台</h1>
        <p className="hero-sub">输入 SVN / Git 仓库路径，平台将自动检测、分类并按规则集进行多维静态审查。</p>
      </div>

      <div className="card home-card fade-in">
        <label className="field-label"><Icon name="git" size={14} /> 仓库路径</label>
        <div className="path-input">
          <span className="pi-proto mono">{path.startsWith("http") ? "https" : "svn"}</span>
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

        <div className="route-grid">
          {WORKFLOWS.map((workflow) => (
            <div
              key={workflow.key}
              className={`route-card${detected === workflow.key ? " active" : ""}`}
              onClick={() =>
                setPath(
                  workflow.key === "hcyt"
                    ? "svn://10.18.32.7/datawh/branches/2026Q2/hcyt"
                    : workflow.key === "fine-report"
                      ? "https://git.intra/report/fine-report.git"
                      : "svn://10.18.32.7/pay/nups/trunk",
                )
              }
            >
              <span className="rc-ico" style={{ color: workflow.color }}><Icon name={workflow.icon} size={18} /></span>
              <span className="rc-body">
                <span className="rc-name">{workflow.name}</span>
                <span className="rc-kw mono">{workflow.kw}</span>
              </span>
              {detected === workflow.key ? <span className="rc-flag"><Icon name="check" size={13} stroke={2.6} /></span> : null}
            </div>
          ))}
        </div>
        <p className="route-hint"><Icon name="info" size={12} /> 根据路径中的关键字自动路由到对应工作流</p>

        {projectsState.loading ? <p className="route-hint">正在加载后端项目列表...</p> : null}
        {projectsState.error ? <p className="route-hint">项目列表接口不可用，当前仍可使用本地原型流程。</p> : null}
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
          <span className="ha-meta mono">{detected ? WORKFLOWS.find((workflow) => workflow.key === detected)?.name : "未识别工作流"}</span>
          <button className="btn primary lg" onClick={submit} disabled={!path.trim()}>
            <Icon name="play" size={15} stroke={2.2} /> 提交审查
          </button>
        </div>
      </div>

      <div className="recent-block fade-in">
        <div className="subhead"><Icon name="clock" size={12} /> 最近审查</div>
        {tasksState.loading ? <div className="card recent-list">正在加载任务列表...</div> : null}
        <div className="card recent-list">
          {recentList.length ? recentList.map((item, index) => {
            const workflow = WORKFLOWS.find((entry) => entry.key === item.wf) || WORKFLOWS[0];
            const tone = item.status === "pass" ? "ok" : item.status === "fail" ? "err" : "warn";
            return (
              <div key={`${item.rev}-${index}`} className="recent-row" onClick={() => onSubmit({ path: item.repo, ai: false, dbg: false, workflow: item.wf })}>
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
        {tasksState.error ? <p className="route-hint">任务接口不可用，当前展示 mock 数据。</p> : null}
      </div>
    </div>
  );
}
