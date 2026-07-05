import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "./components/ui";
import { TweakColor, TweaksPanel, TweakRadio, TweakSection, TweakToggle, useTweaks } from "./components/tweaksPanel";
import { useAsyncResource } from "./hooks/useAsyncResource";
import { useAuditRun } from "./hooks/useAuditRun";
import { FINEREPORT_DATA, HCYT_DATA, NUPS_DATA, WORKFLOWS } from "./mock/data";
import { reviewService } from "./services/reviewService";

const HomePage = lazy(() => import("./pages/HomePage"));
const ResultsPage = lazy(() => import("./pages/ResultsPage").then((module) => ({ default: module.ResultsPage })));
const FineReportResultsPage = lazy(() => import("./pages/FineReportPage").then((module) => ({ default: module.FineReportResultsPage })));
const NupsResultsPage = lazy(() => import("./pages/NupsPage").then((module) => ({ default: module.NupsResultsPage })));
const NUPS_NAV = [
  { id: "overview", label: "概览", icon: "layers" },
  { id: "changes", label: "变更文件", icon: "git", get: (data) => data.changes, neutral: true },
  { id: "nups-sql", label: "NUPS SQL", icon: "db", get: (data) => data.sqlChecks, neutral: true },
  { id: "nups-py", label: "加工程序", icon: "python", get: (data) => data.pyScripts, neutral: true },
];
const SECTION_NAV = [
  { id: "overview", label: "概览", icon: "layers" },
  { id: "changes", label: "变更文件", icon: "git", get: (data) => data.changes, neutral: true },
  { id: "conflict", label: "trunk 冲突", icon: "conflict", get: (data) => data.conflicts },
  { id: "dws", label: "DWS SQL", icon: "db", get: (data) => data.dws },
  { id: "hive", label: "Hive SQL", icon: "db", get: (data) => data.hive },
  { id: "python", label: "Python 脚本", icon: "python", get: (data) => data.pyScripts, neutral: true },
  { id: "sbin", label: "后置脚本", icon: "terminal", get: (data) => data.sbin },
  { id: "config", label: "配置文件", icon: "cog", get: (data) => data.config },
  { id: "recv", label: "收卸配置", icon: "download", get: (data) => data.recv },
  { id: "schedule", label: "调度表", icon: "grid", get: (data) => data.schedule.rows.filter((row) => row.level !== "ok") },
  { id: "reftables", label: "引用表汇总", icon: "db", get: (data) => data.refTables, neutral: true },
  { id: "deps", label: "作业依赖", icon: "flow", get: (data) => data.deps, neutral: true },
];
const FR_NAV = [
  { id: "overview", label: "概览", icon: "layers" },
  { id: "reports", label: "报表检查", icon: "grid", get: (data) => data.reports, neutral: true },
  { id: "reftables", label: "引用表汇总", icon: "db", get: (data) => data.refTables, neutral: true },
];

const DEBUG_LINES = [
  { t: "INFO", m: "svn checkout 启动 -> 目标版本 r48217" },
  { t: "INFO", m: "文件分类完成，DWS x3 / Hive x2 / Python x2 / 配置 x2" },
  { t: "RULE", m: "加载规则集 hcyt-ruleset@v3.4.2（共 87 条）" },
  { t: "WARN", m: "dws_cust_asset_d.sql:18 命中规则 [禁止视图创建]" },
  { t: "ERR", m: "dws_risk_tag_d.sql:33 命中规则 [笛卡尔积风险]" },
  { t: "INFO", m: "审查完成 / 错误 7 / 警告 14 / 耗时 1m47s" },
];

const TWEAK_DEFAULTS = {
  dark: true,
  density: "standard",
  sampleState: "fail",
  variant: "standard",
  showAi: true,
  accent: "#3358d4",
};

function DebugConsole({ open, onClose, logs }) {
  const realLines = logs?.length
    ? logs.map((entry) => ({ t: entry.level === "ERR" ? "ERR" : entry.level === "WARN" ? "WARN" : "INFO", m: entry.msg, ts: entry.ts }))
    : null;
  const lines = realLines || DEBUG_LINES;
  return (
    <div className={`debug-drawer${open ? " open" : ""}`}>
      <div className="dbg-head">
        <Icon name="terminal" size={14} /> 调试日志
        <span className="badge mono" style={{ marginLeft: 8 }}>{realLines ? "svn_check 实时日志" : "演示日志"}</span>
        <span style={{ flex: 1 }} />
        <button className="iconbtn" style={{ width: 26, height: 26 }} onClick={onClose}><Icon name="x" size={14} /></button>
      </div>
      <div className="dbg-body mono">
        {lines.map((line, index) => (
          <div key={index} className="dbg-line">
            <span className="dbg-ts">{line.ts || `14:22:${(8 + index * 11).toString().padStart(2, "0")}`}</span>
            <span className={`dbg-tag ${line.t.trim().toLowerCase()}`}>{line.t}</span>
            <span className="dbg-msg">{line.m}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function RunningView({ task }) {
  const progress = task?.progress ?? 0;
  const step = task?.step || "排队中";
  const recentLogs = (task?.logs || []).slice(-12);
  return (
    <div className="card fade-in" style={{ padding: 24 }}>
      <div className="section-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Icon name="clock" size={16} /> 审查任务执行中
      </div>
      <p className="muted" style={{ margin: "10px 0 6px" }}>当前步骤：{step}</p>
      <div style={{ height: 8, borderRadius: 4, background: "var(--border)", overflow: "hidden", margin: "10px 0 16px" }}>
        <div style={{ height: "100%", width: `${progress}%`, background: "var(--accent)", transition: "width .4s" }} />
      </div>
      {recentLogs.length ? (
        <pre className="mono" style={{ fontSize: "var(--fs-xs)", color: "var(--text-2)", whiteSpace: "pre-wrap", margin: 0 }}>
          {recentLogs.map((entry) => `[${entry.ts}] ${entry.msg}`).join("\n")}
        </pre>
      ) : null}
    </div>
  );
}

function FailedView({ task, onBack }) {
  const recentLogs = (task?.logs || []).slice(-20);
  return (
    <div className="card fade-in" style={{ padding: 24, borderColor: "var(--err)" }}>
      <div className="section-title" style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--err-fg)" }}>
        <Icon name="x" size={16} /> 审查任务执行失败
      </div>
      <p className="muted" style={{ margin: "10px 0" }}>{task?.error || "任务异常结束，未生成报告。"}</p>
      {recentLogs.length ? (
        <pre className="mono" style={{ fontSize: "var(--fs-xs)", color: "var(--text-2)", whiteSpace: "pre-wrap", margin: "0 0 14px" }}>
          {recentLogs.map((entry) => `[${entry.ts}] ${entry.level} ${entry.msg}`).join("\n")}
        </pre>
      ) : null}
      <button className="btn primary" onClick={onBack}><Icon name="chevron" size={14} style={{ transform: "rotate(180deg)" }} /> 返回首页</button>
    </div>
  );
}

function Rail({ data, active, onJump, collapsed, params, nav, mobileOpen }) {
  return (
    <aside className={`rail${collapsed ? " collapsed" : ""}${mobileOpen ? " mobile-open" : ""}`}>
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

function PageFallback() {
  return (
    <div className="card" style={{ padding: 24 }}>
      <div className="section-title">Loading...</div>
      <p className="muted" style={{ margin: "8px 0 0" }}>Page resources are loading.</p>
    </div>
  );
}

export default function App() {
  const showTweaksPanel = import.meta.env.DEV;
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [view, setView] = useState("home");
  const [params, setParams] = useState({ path: "", ai: false, dbg: false, workflow: "hcyt", taskId: null });
  const [active, setActive] = useState("overview");
  const [dbgOpen, setDbgOpen] = useState(false);
  const [railOpen, setRailOpen] = useState(false);
  const contentRef = useRef(null);
  const registry = useRef(new Map());

  const isFR = params.workflow === "fine-report";
  const isNups = params.workflow === "nups";
  const run = useAuditRun(view === "results" ? params.taskId : null);
  const liveData = run.report;
  const mockDataset = isNups ? NUPS_DATA : (isFR ? FINEREPORT_DATA : HCYT_DATA);
  const data = liveData || (t.sampleState === "pass" ? mockDataset.PASS : mockDataset.FAIL);
  const navList = isNups ? NUPS_NAV : (isFR ? FR_NAV : SECTION_NAV);
  const workflowName = WORKFLOWS.find((workflow) => workflow.key === params.workflow)?.name || params.workflow;
  const aiEnabled = liveData ? Boolean(liveData.ai) : (params.ai || t.showAi);
  const projectsState = useAsyncResource(() => reviewService.getProjects(), [], { enabled: view === "home" });
  const tasksState = useAsyncResource(() => reviewService.getAuditTasks(), [view], { enabled: view === "home" });
  const auditResultsState = useAsyncResource(() => reviewService.getAuditResults(), [], {
    enabled: view === "results" && !isFR && !params.taskId,
  });
  const fineReportItemsState = useAsyncResource(() => reviewService.getFineReportItems(), [], {
    enabled: view === "results" && isFR && !params.taskId,
  });

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
      return await reviewService.createAuditTask({
        repo: payload.path,
        sourceType: payload.sourceType || "svn",
        workflow: payload.workflow,
        ai_enabled: payload.ai,
        debug_enabled: payload.dbg,
      });
    } catch (error) {
      return { error: error.message || "Failed to create audit task" };
    }
  }

  function submit(nextParams) {
    setParams({ taskId: null, ...nextParams });
    setView("results");
    setActive("overview");
    setDbgOpen(nextParams.dbg);
    setRailOpen(false);
    contentRef.current?.scrollTo({ top: 0 });
  }

  const taskFailed = !!params.taskId && !!run.task && !run.running && !liveData;

  const page = useMemo(() => {
    if (view === "home") {
      return (
        <Suspense fallback={<PageFallback />}>
          <HomePage
            onSubmit={submit}
            projectsState={projectsState}
            tasksState={tasksState}
            onCreateTask={handleCreateTask}
          />
        </Suspense>
      );
    }
    if (params.taskId && (run.running || (!run.task && !run.error))) {
      return <RunningView task={run.task} />;
    }
    if (taskFailed) {
      return <FailedView task={run.task} onBack={() => setView("home")} />;
    }
    if (isNups) {
      return (
        <Suspense fallback={<PageFallback />}>
          <NupsResultsPage d={data} aiEnabled={aiEnabled} reg={reg} />
        </Suspense>
      );
    }
    if (isFR) {
      return (
        <Suspense fallback={<PageFallback />}>
          <FineReportResultsPage
            d={data}
            aiEnabled={aiEnabled}
            reg={reg}
            apiState={liveData ? null : fineReportItemsState}
          />
        </Suspense>
      );
    }
    return (
      <Suspense fallback={<PageFallback />}>
        <ResultsPage
          d={data}
          aiEnabled={aiEnabled}
          variant={t.variant}
          reg={reg}
          onJump={jump}
          apiState={liveData ? null : auditResultsState}
        />
      </Suspense>
    );
  }, [aiEnabled, auditResultsState, data, fineReportItemsState, isFR, isNups, liveData, params.taskId, projectsState, run.error, run.running, run.task, t.variant, taskFailed, tasksState, view]);

  return (
    <div className={`app${view === "home" ? " no-rail" : ""}`}>
      {view !== "home" ? (
        <>
          <div
            className={`rail-overlay${railOpen ? " shown" : ""}`}
            onClick={() => setRailOpen(false)}
          />
          <Rail
            data={data}
            active={active}
            onJump={(id) => { jump(id); setRailOpen(false); }}
            params={params}
            nav={navList}
            mobileOpen={railOpen}
          />
        </>
      ) : null}
      <div className="main">
        <header className="topbar">
          {view === "results" ? (
            <>
              <button className="iconbtn mobile-menu-btn" title="导航菜单" onClick={() => setRailOpen((o) => !o)}>
                <Icon name="menu" size={16} />
              </button>
              <button className="btn ghost sm" onClick={() => setView("home")}><Icon name="chevron" size={14} style={{ transform: "rotate(180deg)" }} /> 新审查</button>
              <div className="crumb">
                <span className="seg">{workflowName}</span>
                <span className="sep">/</span>
                <span className="seg cur mono">{liveData ? liveData.task.revision : data.task.revision}</span>
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

        {view === "results" && (params.dbg || run.task?.logs?.length) ? (
          <DebugConsole open={dbgOpen} onClose={() => setDbgOpen(false)} logs={run.task?.logs} />
        ) : null}
      </div>

      {showTweaksPanel ? <TweaksPanel title="Tweaks">
        <TweakSection label="主题" />
        <TweakToggle label="深色模式" value={t.dark} onChange={(value) => setTweak("dark", value)} />
        <TweakColor label="主题色" value={t.accent} options={["#3358d4", "#0e7d6b", "#b3531d", "#c0392f"]} onChange={(value) => setTweak("accent", value)} />
        <TweakRadio label="密度" value={t.density} options={[{ value: "compact", label: "紧凑" }, { value: "standard", label: "标准" }, { value: "comfortable", label: "宽松" }]} onChange={(value) => setTweak("density", value)} />
        <TweakSection label="示例数据" />
        <TweakRadio label="审查结果" value={t.sampleState} options={[{ value: "fail", label: "未通过" }, { value: "pass", label: "通过" }]} onChange={(value) => setTweak("sampleState", value)} />
        <TweakToggle label="AI 面板" value={t.showAi} onChange={(value) => setTweak("showAi", value)} />
        <TweakSection label="结果布局" />
        <TweakRadio label="布局变体" value={t.variant} options={[{ value: "standard", label: "标准" }, { value: "board", label: "看板" }, { value: "issues", label: "问题优先" }]} onChange={(value) => setTweak("variant", value)} />
      </TweaksPanel> : null}
    </div>
  );
}
