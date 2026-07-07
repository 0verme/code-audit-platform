/* Home / public entry page — path input, toggles, auto-route detection. */

const WORKFLOWS = [
  { key: "hcyt", kw: "/hcyt/", name: "HCYT 湖仓审查", desc: "DWS / Hive SQL · Python · 调度表 · 收卸配置", icon: "db", color: "var(--accent)" },
  { key: "fine-report", kw: "/fine-report/", name: "FineReport 报表审查", desc: "报表模板 · 数据集 · 参数与权限校验", icon: "grid", color: "var(--ok)" },
  { key: "nups", kw: "/nups/", name: "NUPS 统一支付审查", desc: "接口契约 · 配置文件 · 联调依赖检查", icon: "layers", color: "var(--warn)" },
];

const RECENT = [
  { repo: "svn+ssh://svn.example.com/example/repo/branches/demo", wf: "hcyt", rev: "r48217", status: "fail", when: "10 分钟前", who: "zhanglei" },
  { repo: "svn+ssh://svn.example.com/example/repo/branches/demo", wf: "hcyt", rev: "r48231", status: "pass", when: "32 分钟前", who: "wangmin" },
  { repo: "https://git.example.com/report/fine-report.git", wf: "fine-report", rev: "8f1c2ad", status: "pass", when: "1 小时前", who: "liyang" },
  { repo: "svn+ssh://svn.example.com/example/repo/trunk/nups", wf: "nups", rev: "r9021", status: "warn", when: "2 小时前", who: "chenhao" },
];

function detectWorkflow(path) {
  const p = (path || "").toLowerCase();
  for (const w of WORKFLOWS) if (p.includes(w.kw)) return w.key;
  if (p.includes("hcyt")) return "hcyt";
  if (p.includes("report")) return "fine-report";
  if (p.includes("nups") || p.includes("pay")) return "nups";
  return null;
}

function Toggle({ on, onChange, label, desc, icon }) {
  return (
    <div className="row-toggle" onClick={() => onChange(!on)}>
      <span className="rt-ico"><Icon name={icon} size={16} /></span>
      <span className="rt-text">
        <span className="rt-label">{label}</span>
        <span className="rt-desc">{desc}</span>
      </span>
      <span className={"switch" + (on ? " on" : "")}><span className="knob" /></span>
    </div>
  );
}

function HomePage({ onSubmit }) {
  const [path, setPath] = React.useState("svn+ssh://svn.example.com/example/repo/branches/demo/hcyt");
  const [ai, setAi] = React.useState(false);
  const [dbg, setDbg] = React.useState(false);
  const detected = detectWorkflow(path);

  function submit() {
    if (!path.trim()) return;
    onSubmit({ path: path.trim(), ai, dbg, workflow: detected || "hcyt" });
  }

  return (
      <div className="home-wrap">
        <div className="home-hero fade-in">
          <div className="hero-badge"><Dot tone="ok" pulse /> 审查引擎在线 · v3.4.2</div>
          <h1 className="hero-title">代码提交审查平台</h1>
          <p className="hero-sub">输入 SVN / Git 仓库路径，平台将自动检出、分类并按规则集进行多维静态审查。</p>
        </div>

        <div className="card home-card fade-in">
          <label className="field-label"><Icon name="git" size={14} /> 仓库路径</label>
          <div className="path-input">
            <span className="pi-proto mono">{path.startsWith("http") ? "https" : "svn"}</span>
            <input className="pi-field mono" value={path} spellCheck={false}
              onChange={e => setPath(e.target.value)}
              onKeyDown={e => e.key === "Enter" && submit()}
              placeholder="https://svn.example.com/... or https://git.example.com/..." />
            {detected
              ? <span className="pi-detect"><Dot tone="ok" /> 已识别</span>
              : <span className="pi-detect muted"><Dot /> 待识别</span>}
          </div>

          <div className="route-grid">
            {WORKFLOWS.map(w => (
              <div key={w.key} className={"route-card" + (detected === w.key ? " active" : "")}
                onClick={() => setPath(p => {
                  const base = "svn+ssh://svn.example.com/example/repo/branches/demo";
                  return w.key === "hcyt" ? base + "/hcyt"
                    : w.key === "fine-report" ? "https://git.example.com/report/fine-report.git"
                    : "svn+ssh://svn.example.com/example/repo/trunk/nups";
                })}>
                <span className="rc-ico" style={{ color: w.color }}><Icon name={w.icon} size={18} /></span>
                <span className="rc-body">
                  <span className="rc-name">{w.name}</span>
                  <span className="rc-kw mono">{w.kw}</span>
                </span>
                {detected === w.key ? <span className="rc-flag"><Icon name="check" size={13} stroke={2.6} /></span> : null}
              </div>
            ))}
          </div>
          <p className="route-hint"><Icon name="info" size={12} /> 根据路径中的关键字自动路由到对应工作流</p>

          <div className="divline" />

          <div className="toggles">
            <Toggle on={ai} onChange={setAi} icon="sparkle" label="接入本地 AI 大模型" desc="启用后追加 AI 语义分析与修复建议（默认关闭）" />
            <Toggle on={dbg} onChange={setDbg} icon="terminal" label="调试日志" desc="输出检出、分类与规则执行的详细日志（默认关闭）" />
          </div>

          <div className="home-actions">
            <span className="ha-meta mono">{detected ? WORKFLOWS.find(w => w.key === detected).name : "未识别工作流"}</span>
            <button className="btn primary lg" onClick={submit} disabled={!path.trim()}>
              <Icon name="play" size={15} stroke={2.2} /> 提交审查
            </button>
          </div>
        </div>

        <div className="recent-block fade-in">
          <div className="subhead"><Icon name="clock" size={12} /> 最近审查</div>
          <div className="card recent-list">
            {RECENT.map((r, i) => {
              const wf = WORKFLOWS.find(w => w.key === r.wf);
              const tone = r.status === "pass" ? "ok" : r.status === "fail" ? "err" : "warn";
              return (
                <div key={i} className="recent-row" onClick={() => onSubmit({ path: r.repo, ai: false, dbg: false, workflow: r.wf })}>
                  <Dot tone={tone} />
                  <span className="rr-rev mono">{r.rev}</span>
                  <span className="rr-repo mono">{r.repo}</span>
                  <span className="rr-wf"><Icon name={wf.icon} size={12} style={{ color: wf.color }} /> {wf.name}</span>
                  <span className="rr-who">{r.who}</span>
                  <span className="rr-when">{r.when}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
  );
}

Object.assign(window, { HomePage, WORKFLOWS, detectWorkflow });
