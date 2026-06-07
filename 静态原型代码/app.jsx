/* App shell: rail nav, topbar, routing (home ↔ results), tweaks, debug console. */

const { useState, useEffect, useRef, useMemo } = React;

const SECTION_NAV = [
  { id: "overview", label: "概览", icon: "layers" },
  { id: "changes", label: "变更文件", icon: "git", get: d => d.changes, neutral: true },
  { id: "conflict", label: "trunk 冲突", icon: "conflict", get: d => d.conflicts },
  { id: "dws", label: "DWS SQL", icon: "db", get: d => d.dws },
  { id: "hive", label: "Hive SQL", icon: "db", get: d => d.hive },
  { id: "python", label: "Python 脚本", icon: "python", get: d => d.pyScripts, neutral: true },
  { id: "sbin", label: "后置脚本", icon: "terminal", get: d => d.sbin },
  { id: "config", label: "配置文件", icon: "cog", get: d => d.config },
  { id: "recv", label: "收卸配置", icon: "download", get: d => d.recv },
  { id: "schedule", label: "调度表", icon: "grid", get: d => d.schedule.rows.filter(r => r.level !== "ok") },
  { id: "reftables", label: "引用表汇总", icon: "db", get: d => d.refTables, neutral: true },
  { id: "deps", label: "作业依赖", icon: "flow", get: d => d.deps, neutral: true },
];

const DEBUG_LINES = [
  { t: "INFO", m: "svn checkout 启动 → 目标版本 r48217" },
  { t: "INFO", m: "检出完成，共 23 个变更文件，用时 12.4s" },
  { t: "INFO", m: "文件分类：DWS×3 Hive×3 Python×2 配置×3 调度×1" },
  { t: "RULE", m: "加载规则集 hcyt-ruleset@v3.4.2（共 87 条）" },
  { t: "WARN", m: "dws_cust_asset_d.sql:18 命中规则 [禁止视图创建]" },
  { t: "ERR ", m: "dws_risk_tag_d.sql:33 命中规则 [笛卡尔积风险]" },
  { t: "RULE", m: "调度表循环依赖扫描：检测到 1 处 A→B→A" },
  { t: "INFO", m: "审查完成 · 错误 7 · 警告 14 · 耗时 1m47s" },
];

function DebugConsole({ open, onClose }) {
  return (
    <div className={"debug-drawer" + (open ? " open" : "")}>
      <div className="dbg-head">
        <Icon name="terminal" size={14} /> 调试日志
        <span className="badge mono" style={{ marginLeft: 8 }}>hcyt-ruleset@v3.4.2</span>
        <span style={{ flex: 1 }} />
        <button className="iconbtn" style={{ width: 26, height: 26 }} onClick={onClose}><Icon name="x" size={14} /></button>
      </div>
      <div className="dbg-body mono">
        {DEBUG_LINES.map((l, i) => (
          <div key={i} className="dbg-line">
            <span className="dbg-ts">14:22:{(8 + i * 11).toString().padStart(2, "0")}</span>
            <span className={"dbg-tag " + l.t.trim().toLowerCase()}>{l.t}</span>
            <span className="dbg-msg">{l.m}</span>
          </div>
        ))}
        <div className="dbg-line"><span className="dbg-ts" /><span className="dbg-cursor">▍</span></div>
      </div>
    </div>
  );
}

function Rail({ view, data, active, onJump, collapsed, params, nav }) {
  return (
    <aside className={"rail" + (collapsed ? " collapsed" : "")}>
      <div className="rail-head">
        <div className="brand-mark">审</div>
        {!collapsed && (
          <div style={{ minWidth: 0 }}>
            <div className="brand-name">代码审查平台</div>
            <div className="brand-sub">Code Review</div>
          </div>
        )}
      </div>
      <div className="rail-scroll">
        <>
            <div className="rail-group-label">审查结果</div>
            {nav.map(s => {
              if (s.id === "ai") return null;
              const rows = s.get ? s.get(data) : null;
              let tone = null, count = null;
              if (rows) {
                count = rows.length;
                if (!s.neutral) tone = window.levelOf(rows) || "ok";
              }
              return (
                <div key={s.id} className={"navitem" + (active === s.id ? " active" : "")} onClick={() => onJump(s.id)}>
                  <span className="ni-ico"><Icon name={s.icon} size={15} /></span>
                  {!collapsed && <span className="ni-label">{s.label}</span>}
                  {!collapsed && count != null && (
                    <span className={"ni-count" + (tone ? " " + tone : "")}>{count}</span>
                  )}
                </div>
              );
            })}
            {params && params.ai && (
              <div className={"navitem" + (active === "ai" ? " active" : "")} onClick={() => onJump("ai")}>
                <span className="ni-ico" style={{ color: "var(--accent)" }}><Icon name="sparkle" size={15} /></span>
                {!collapsed && <span className="ni-label">AI 分析</span>}
              </div>
            )}
          </>
      </div>
    </aside>
  );
}

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "dark": false,
  "density": "standard",
  "sampleState": "fail",
  "variant": "standard",
  "showAi": true,
  "accent": "#3358d4"
}/*EDITMODE-END*/;

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [view, setView] = useState("home");
  const [params, setParams] = useState({ path: "", ai: false, dbg: false, workflow: "hcyt" });
  const [active, setActive] = useState("overview");
  const [dbgOpen, setDbgOpen] = useState(false);

  const isFR = params.workflow === "fine-report";
  const dataset = isFR ? FINEREPORT_DATA : HCYT_DATA;
  const data = t.sampleState === "pass" ? dataset.PASS : dataset.FAIL;
  const navList = isFR ? FR_NAV : SECTION_NAV;
  const wfName = (WORKFLOWS.find(w => w.key === params.workflow) || {}).name || params.workflow;
  const aiEnabled = (params.ai || t.showAi);

  // apply theme + density + accent
  useEffect(() => {
    const r = document.documentElement;
    r.dataset.theme = t.dark ? "dark" : "light";
    if (t.density === "standard") r.removeAttribute("data-density");
    else r.dataset.density = t.density;
    r.style.setProperty("--accent", t.accent);
  }, [t.dark, t.density, t.accent]);

  const contentRef = useRef(null);
  const registry = useRef(new Map());
  const reg = (id, ref, setOpen) => registry.current.set(id, { ref, setOpen });

  function jump(id) {
    setActive(id);
    if (id === "overview") { contentRef.current.scrollTo({ top: 0, behavior: "smooth" }); return; }
    const entry = registry.current.get(id);
    const el = document.getElementById("sec-" + id);
    if (entry) entry.setOpen(true);
    requestAnimationFrame(() => {
      const node = document.getElementById("sec-" + id);
      if (!node || !contentRef.current) return;
      const c = contentRef.current;
      const top = node.getBoundingClientRect().top - c.getBoundingClientRect().top + c.scrollTop - 12;
      c.scrollTo({ top, behavior: "smooth" });
    });
  }

  // scroll spy
  useEffect(() => {
    if (view !== "results") return;
    const c = contentRef.current;
    if (!c) return;
    const onScroll = () => {
      const cTop = c.getBoundingClientRect().top;
      let cur = "overview";
      for (const s of navList) {
        if (s.id === "overview") continue;
        const n = document.getElementById("sec-" + s.id);
        if (n && n.getBoundingClientRect().top - cTop < 120) cur = s.id;
      }
      setActive(cur);
    };
    c.addEventListener("scroll", onScroll, { passive: true });
    return () => c.removeEventListener("scroll", onScroll);
  }, [view, t.variant, aiEnabled, t.sampleState]);

  function submit(p) {
    setParams(p);
    setView("results");
    setActive("overview");
    setDbgOpen(p.dbg);
    if (contentRef.current) contentRef.current.scrollTo({ top: 0 });
  }

  return (
    <div className={"app" + (view === "home" ? " no-rail" : "")}>
      {view !== "home" ? <Rail view={view} data={data} active={active} onJump={jump} params={params} nav={navList} /> : null}
      <div className="main">
        <header className="topbar">
          {view === "results" ? (
            <>
              <button className="btn ghost sm" onClick={() => setView("home")}><Icon name="chevron" size={14} style={{ transform: "rotate(180deg)" }} /> 新审查</button>
              <div className="crumb">
                <span className="seg">{wfName}</span>
                <span className="sep">/</span>
                <span className="seg cur mono">{data.task.revision}</span>
                <span className="path">{params.path || data.task.repo}</span>
              </div>
            </>
          ) : (
            <div className="crumb"><span className="seg cur">首页 · 提交审查</span></div>
          )}
          <span className="topbar-spacer" />
          {view === "results" && (
            <button className={"iconbtn" + (dbgOpen ? " active-ic" : "")} title="调试日志" onClick={() => setDbgOpen(o => !o)} style={dbgOpen ? { borderColor: "var(--accent)", color: "var(--accent)" } : null}>
              <Icon name="terminal" size={16} />
            </button>
          )}
          <button className="iconbtn" title="切换主题" onClick={() => setTweak("dark", !t.dark)}>
            <Icon name={t.dark ? "sun" : "moon"} size={16} />
          </button>
        </header>

        <div className="content" ref={contentRef}>
          {view === "home"
            ? <HomePage onSubmit={submit} />
            : <div className="content-inner">
                {isFR
                  ? <FineReportResultsPage d={data} aiEnabled={aiEnabled} reg={reg} onJump={jump} />
                  : <ResultsPage d={data} aiEnabled={aiEnabled} variant={t.variant} reg={reg} onJump={jump} />}
              </div>}
        </div>

        {view === "results" && params.dbg ? <DebugConsole open={dbgOpen} onClose={() => setDbgOpen(false)} /> : null}
      </div>

      <TweaksPanel title="Tweaks">
        <TweakSection label="主题" />
        <TweakToggle label="深色模式" value={t.dark} onChange={v => setTweak("dark", v)} />
        <TweakColor label="主题色" value={t.accent}
          options={["#3358d4", "#0e7d6b", "#b3531d", "#7a4ff0", "#c0392f"]}
          onChange={v => setTweak("accent", v)} />
        <TweakRadio label="密度" value={t.density}
          options={[{ value: "compact", label: "紧凑" }, { value: "standard", label: "标准" }, { value: "comfortable", label: "宽松" }]}
          onChange={v => setTweak("density", v)} />
        <TweakSection label="示例数据" />
        <TweakRadio label="审查结果" value={t.sampleState}
          options={[{ value: "fail", label: "未通过" }, { value: "pass", label: "通过" }]}
          onChange={v => setTweak("sampleState", v)} />
        <TweakToggle label="AI 分析面板" value={t.showAi} onChange={v => setTweak("showAi", v)} />
        <TweakSection label="结果页布局" />
        <TweakRadio label="布局变体" value={t.variant}
          options={[{ value: "standard", label: "标准" }, { value: "board", label: "看板" }, { value: "issues", label: "问题优先" }]}
          onChange={v => setTweak("variant", v)} />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
