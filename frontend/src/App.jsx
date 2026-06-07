import { useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "./components/ui";
import { TweakColor, TweaksPanel, TweakRadio, TweakSection, TweakToggle, useTweaks } from "./components/tweaksPanel";
import { useAsyncResource } from "./hooks/useAsyncResource";
import { FINEREPORT_DATA, HCYT_DATA, WORKFLOWS } from "./mock/data";
import HomePage from "./pages/HomePage";
import { FineReportResultsPage, FR_NAV } from "./pages/FineReportPage";
import { ResultsPage, SECTION_NAV } from "./pages/ResultsPage";
import { reviewService } from "./services/reviewService";

const DEBUG_LINES = [
  { t: "INFO", m: "svn checkout 启动 -> 目标版本 r48217" },
  { t: "INFO", m: "文件分类完成，DWS x3 / Hive x2 / Python x2 / 配置 x2" },
  { t: "RULE", m: "加载规则集 hcyt-ruleset@v3.4.2（共 87 条）" },
  { t: "WARN", m: "dws_cust_asset_d.sql:18 命中规则 [禁止视图创建]" },
  { t: "ERR", m: "dws_risk_tag_d.sql:33 命中规则 [笛卡尔积风险]" },
  { t: "INFO", m: "审查完成 / 错误 7 / 警告 14 / 耗时 1m47s" },
];

const TWEAK_DEFAULTS = {
  dark: false,
  density: "standard",
  sampleState: "fail",
  variant: "standard",
  showAi: true,
  accent: "#3358d4",
};

function DebugConsole({ open, onClose }) {
  return (
    <div className={`debug-drawer${open ? " open" : ""}`}>
      <div className="dbg-head">
        <Icon name="terminal" size={14} /> 调试日志
        <span className="badge mono" style={{ marginLeft: 8 }}>hcyt-ruleset@v3.4.2</span>
        <span style={{ flex: 1 }} />
        <button className="iconbtn" style={{ width: 26, height: 26 }} onClick={onClose}><Icon name="x" size={14} /></button>
      </div>
      <div className="dbg-body mono">
        {DEBUG_LINES.map((line, index) => (
          <div key={index} className="dbg-line">
            <span className="dbg-ts">14:22:{(8 + index * 11).toString().padStart(2, "0")}</span>
            <span className={`dbg-tag ${line.t.trim().toLowerCase()}`}>{line.t}</span>
            <span className="dbg-msg">{line.m}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Rail({ data, active, onJump, collapsed, params, nav }) {
  return (
    <aside className={`rail${collapsed ? " collapsed" : ""}`}>
      <div className="rail-head">
        <div className="brand-mark">审</div>
        {!collapsed ? (
          <div style={{ minWidth: 0 }}>
            <div className="brand-name">代码审查平台</div>
            <div className="brand-sub">Code Review</div>
          </div>
        ) : null}
      </div>
      <div className="rail-scroll">
        <div className="rail-group-label">审查结果</div>
        {nav.map((section) => {
          if (section.id === "ai") return null;
          const rows = section.get ? section.get(data) : null;
          const tone = rows && !section.neutral ? (rows.some((item) => item.level === "err") ? "err" : rows.some((item) => item.level === "warn") ? "warn" : "ok") : null;
          const count = rows ? rows.length : null;
          return (
            <div key={section.id} className={`navitem${active === section.id ? " active" : ""}`} onClick={() => onJump(section.id)}>
              <span className="ni-ico"><Icon name={section.icon} size={15} /></span>
              {!collapsed ? <span className="ni-label">{section.label}</span> : null}
              {!collapsed && count != null ? <span className={`ni-count${tone ? ` ${tone}` : ""}`}>{count}</span> : null}
            </div>
          );
        })}
        {params.ai ? (
          <div className={`navitem${active === "ai" ? " active" : ""}`} onClick={() => onJump("ai")}>
            <span className="ni-ico" style={{ color: "var(--accent)" }}><Icon name="sparkle" size={15} /></span>
            {!collapsed ? <span className="ni-label">AI 分析</span> : null}
          </div>
        ) : null}
      </div>
    </aside>
  );
}

export default function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [view, setView] = useState("home");
  const [params, setParams] = useState({ path: "", ai: false, dbg: false, workflow: "hcyt" });
  const [active, setActive] = useState("overview");
  const [dbgOpen, setDbgOpen] = useState(false);
  const contentRef = useRef(null);
  const registry = useRef(new Map());

  const projectsState = useAsyncResource(() => reviewService.getProjects(), []);
  const tasksState = useAsyncResource(() => reviewService.getAuditTasks(), []);
  const auditResultsState = useAsyncResource(() => reviewService.getAuditResults(), []);
  const fineReportItemsState = useAsyncResource(() => reviewService.getFineReportItems(), []);

  const isFR = params.workflow === "fine-report";
  const dataset = isFR ? FINEREPORT_DATA : HCYT_DATA;
  const data = t.sampleState === "pass" ? dataset.PASS : dataset.FAIL;
  const navList = isFR ? FR_NAV : SECTION_NAV;
  const workflowName = WORKFLOWS.find((workflow) => workflow.key === params.workflow)?.name || params.workflow;

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = t.dark ? "dark" : "light";
    if (t.density === "standard") root.removeAttribute("data-density");
    else root.dataset.density = t.density;
    root.style.setProperty("--accent", t.accent);
  }, [t]);

  function reg(id, ref, setOpen) {
    registry.current.set(id, { ref, setOpen });
  }

  function jump(id) {
    setActive(id);
    if (id === "overview") {
      contentRef.current?.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    const entry = registry.current.get(id);
    entry?.setOpen(true);
    requestAnimationFrame(() => {
      const node = document.getElementById(`sec-${id}`);
      if (!node || !contentRef.current) return;
      const container = contentRef.current;
      const top = node.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop - 12;
      container.scrollTo({ top, behavior: "smooth" });
    });
  }

  useEffect(() => {
    if (view !== "results") return undefined;
    const container = contentRef.current;
    if (!container) return undefined;
    const onScroll = () => {
      const containerTop = container.getBoundingClientRect().top;
      let current = "overview";
      navList.forEach((section) => {
        if (section.id === "overview") return;
        const node = document.getElementById(`sec-${section.id}`);
        if (node && node.getBoundingClientRect().top - containerTop < 120) {
          current = section.id;
        }
      });
      setActive(current);
    };
    container.addEventListener("scroll", onScroll, { passive: true });
    return () => container.removeEventListener("scroll", onScroll);
  }, [navList, view]);

  async function handleCreateTask(payload) {
    try {
      await reviewService.createAuditTask({
        repo: payload.path,
        workflow: payload.workflow,
        ai_enabled: payload.ai,
        debug_enabled: payload.dbg,
      });
    } catch {
      return null;
    }
    return null;
  }

  function submit(nextParams) {
    setParams(nextParams);
    setView("results");
    setActive("overview");
    setDbgOpen(nextParams.dbg);
    contentRef.current?.scrollTo({ top: 0 });
  }

  const page = useMemo(() => {
    if (view === "home") {
      return (
        <HomePage
          onSubmit={submit}
          projectsState={projectsState}
          tasksState={tasksState}
          onCreateTask={handleCreateTask}
        />
      );
    }
    if (isFR) {
      return <FineReportResultsPage d={data} aiEnabled={params.ai || t.showAi} reg={reg} apiState={fineReportItemsState} />;
    }
    return (
      <ResultsPage
        d={data}
        aiEnabled={params.ai || t.showAi}
        variant={t.variant}
        reg={reg}
        onJump={jump}
        apiState={auditResultsState}
      />
    );
  }, [auditResultsState, data, fineReportItemsState, isFR, params.ai, projectsState, t.showAi, t.variant, tasksState, view]);

  return (
    <div className={`app${view === "home" ? " no-rail" : ""}`}>
      {view !== "home" ? <Rail data={data} active={active} onJump={jump} params={params} nav={navList} /> : null}
      <div className="main">
        <header className="topbar">
          {view === "results" ? (
            <>
              <button className="btn ghost sm" onClick={() => setView("home")}><Icon name="chevron" size={14} style={{ transform: "rotate(180deg)" }} /> 新审查</button>
              <div className="crumb">
                <span className="seg">{workflowName}</span>
                <span className="sep">/</span>
                <span className="seg cur mono">{data.task.revision}</span>
                <span className="path">{params.path || data.task.repo}</span>
              </div>
            </>
          ) : (
            <div className="crumb"><span className="seg cur">首页 / 提交审查</span></div>
          )}
          <span className="topbar-spacer" />
          {view === "results" ? (
            <button className={`iconbtn${dbgOpen ? " active-ic" : ""}`} title="调试日志" onClick={() => setDbgOpen((current) => !current)}>
              <Icon name="terminal" size={16} />
            </button>
          ) : null}
          <button className="iconbtn" title="切换主题" onClick={() => setTweak("dark", !t.dark)}>
            <Icon name={t.dark ? "sun" : "moon"} size={16} />
          </button>
        </header>

        <div className="content" ref={contentRef}>
          {view === "home" ? page : <div className="content-inner">{page}</div>}
        </div>

        {view === "results" && params.dbg ? <DebugConsole open={dbgOpen} onClose={() => setDbgOpen(false)} /> : null}
      </div>

      <TweaksPanel title="Tweaks">
        <TweakSection label="主题" />
        <TweakToggle label="深色模式" value={t.dark} onChange={(value) => setTweak("dark", value)} />
        <TweakColor label="主题色" value={t.accent} options={["#3358d4", "#0e7d6b", "#b3531d", "#c0392f"]} onChange={(value) => setTweak("accent", value)} />
        <TweakRadio label="密度" value={t.density} options={[{ value: "compact", label: "紧凑" }, { value: "standard", label: "标准" }, { value: "comfortable", label: "宽松" }]} onChange={(value) => setTweak("density", value)} />
        <TweakSection label="示例数据" />
        <TweakRadio label="审查结果" value={t.sampleState} options={[{ value: "fail", label: "未通过" }, { value: "pass", label: "通过" }]} onChange={(value) => setTweak("sampleState", value)} />
        <TweakToggle label="AI 面板" value={t.showAi} onChange={(value) => setTweak("showAi", value)} />
        <TweakSection label="结果布局" />
        <TweakRadio label="布局变体" value={t.variant} options={[{ value: "standard", label: "标准" }, { value: "board", label: "看板" }, { value: "issues", label: "问题优先" }]} onChange={(value) => setTweak("variant", value)} />
      </TweaksPanel>
    </div>
  );
}
