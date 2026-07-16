import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "./components/ui";
import { TweakColor, TweaksPanel, TweakRadio, TweakSection, TweakToggle, useTweaks } from "./components/tweaksPanel";
import { AUDIT_DATA_MODE, IS_API_MODE } from "./config/api";
import { applyBackendWorkflowDefinitions } from "./config/auditWorkflows";
import { applyAuditSourceDisplayRules } from "./config/auditSourceDisplayConfig";
import { APP_EDITION, APP_NAME, APP_VERSION } from "./config/appMeta";
import { useAsyncResource } from "./hooks/useAsyncResource";
import { mergePartialReport, shouldShowAuditRunFailure, useAuditRun } from "./hooks/useAuditRun";
import { FINEREPORT_DATA, HCYT_DATA, NUPS_DATA, WORKFLOWS } from "./mock/data";
import { reviewService } from "./services/reviewService";
import { hasScheduleTables } from "./utils/hcytResultPresentation";

const HomePage = lazy(() => import("./pages/HomePage"));
const ResultsPage = lazy(() => import("./pages/ResultsPage").then((module) => ({ default: module.ResultsPage })));
const FineReportResultsPage = lazy(() => import("./pages/FineReportPage").then((module) => ({ default: module.FineReportResultsPage })));
const NupsResultsPage = lazy(() => import("./pages/NupsPage").then((module) => ({ default: module.NupsResultsPage })));
const LineagePage = lazy(() => import("./pages/LineagePage").then((module) => ({ default: module.LineagePage })));
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
  { id: "config", label: "配置文件", icon: "cog", get: (data) => data.config },
  { id: "sbin", label: "后置脚本", icon: "terminal", get: (data) => data.sbin },
  { id: "recv", label: "收卸配置", icon: "download", get: (data) => data.recv },
  {
    id: "schedule",
    label: "调度表检查",
    icon: "grid",
    get: (data) => {
      const issues = data.schedule?.rows?.filter((row) => row.level !== "ok") || [];
      return issues.length || !hasScheduleTables(data) ? issues : [{ level: "ok" }];
    },
  },
  {
    id: "python",
    label: "Python 脚本",
    icon: "python",
    get: (data) => {
      const flaggedScripts = (data.pyScripts || []).flatMap((script) => {
        const lint = script.lint || [];
        const result = script.result || [];
        const hasErr = lint.some((item) => item.level === "err") || result.some((item) => item.state === "missing");
        const hasWarn = lint.some((item) => item.level === "warn") || result.some((item) => item.state === "extra");
        if (!hasErr && !hasWarn) return [];
        return [{ script: script.script, level: hasErr ? "err" : "warn" }];
      });
      return flaggedScripts;
    },
    neutral: true,
  },
  { id: "asset-issues", label: "资产问题", icon: "link", get: (data) => data.assetIssues || [] },
];
const FR_NAV = [
  { id: "overview", label: "概览", icon: "layers" },
  { id: "reports", label: "报表检查", icon: "grid", get: (data) => data.reports, neutral: true },
];

const TWEAK_DEFAULTS = {
  density: "standard",
  sampleState: "fail",
  variant: "standard",
  showAi: true,
  accent: "#3358d4",
};

const EMPTY_AUDIT_REPORT = {
  task: {
    status: "warn",
    repo: "",
    sourceRef: "",
    sourceType: "",
    module: "hcyt",
    workflow: "hcyt",
    revision: "-",
    author: "-",
    startedAt: "-",
    duration: "0s",
    changedFiles: 0,
    checks: 0,
    errors: 0,
    warnings: 0,
    conflicts: 0,
  },
  changes: [],
  conflicts: [],
  dws: [],
  hive: [],
  config: [],
  configFiles: [],
  sbin: [],
  recv: [],
  schedule: { summary: { plan: 0, seq: 0, job: 0, cycles: 0, missing: 0 }, rows: [], tables: {} },
  deps: [],
  pyScripts: [],
  refTables: [],
  reports: [],
  menu: null,
  authority: null,
  assetIssues: [],
  unifiedAssetIssues: [],
  lineageSummary: {
    resultTables: [],
    jobs: [],
    recvPlans: [],
    sysNames: [],
    outfiles: [],
    warnings: [],
    stats: {},
  },
  lineageOverlay: { schemaVersion: "1.0", revision: "", programs: [] },
  sqlChecks: {},
  ai: null,
  logs: [],
};

const showTweakControls =
  import.meta.env.DEV || import.meta.env.VITE_SHOW_TWEAKS === "true";

const THEME_STORAGE_KEY = "codeReviewPlatform.theme";
function getInitialTheme() {
  if (typeof window === "undefined") return "light";
  return window.localStorage.getItem(THEME_STORAGE_KEY) === "dark" ? "dark" : "light";
}

function ThemeToggle({ theme, onToggle }) {
  return (
    <button className="iconbtn" title="切换主题" onClick={onToggle}>
      <Icon name={theme === "dark" ? "sun" : "moon"} size={16} />
    </button>
  );
}

function RunningView({ task }) {
  const progress = task?.progress ?? 0;
  const step = task?.step || "排队中";
  const recentLogs = (task?.logs || []).slice(-12);
  return (
    <div className="card fade-in task-state-card">
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
    <div className="card fade-in task-state-card" style={{ borderColor: "var(--err)" }}>
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

function ApiErrorView({ error, onBack }) {
  return (
    <div className="card fade-in task-state-card" style={{ borderColor: "var(--err)" }}>
      <div className="section-title" style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--err-fg)" }}>
        <Icon name="x" size={16} /> 任务接口不可用
      </div>
      <p className="muted" style={{ margin: "10px 0 14px" }}>
        API 模式不会自动降级为 mock。请检查后端服务、网络连接或 VITE_API_BASE_URL。
      </p>
      {error ? <pre className="mono" style={{ fontSize: "var(--fs-xs)", color: "var(--err-fg)", whiteSpace: "pre-wrap", margin: "0 0 14px" }}>{error.message || String(error)}</pre> : null}
      <button className="btn primary" onClick={onBack}><Icon name="chevron" size={14} style={{ transform: "rotate(180deg)" }} /> 返回首页</button>
    </div>
  );
}

function Rail({ data, active, onJump, collapsed, params, nav, mobileOpen }) {
  return (
    <aside className={`rail${collapsed ? " collapsed" : ""}${mobileOpen ? " mobile-open" : ""}`}>
      <div className="rail-head">
        <img className="brand-mark" src="/favicon.svg" alt="代码提交审查平台" />
        {!collapsed ? (
          <div style={{ minWidth: 0 }}>
            <div className="brand-name">代码提交审查平台</div>
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
          if (section.id !== "overview" && count === 0) return null;
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

function AppFooter() {
  return (
    <footer className="app-footer-shell">
      <div className="app-footer">
        <span className="app-footer-copy">{APP_NAME} {APP_EDITION} · {APP_VERSION}</span>
      </div>
    </footer>
  );
}

export default function App() {
  const [, setWorkflowConfigVersion] = useState(0);
  useEffect(() => {
    if (!IS_API_MODE) return;
    reviewService.getAuditWorkflows()
      .then((payload) => {
        applyBackendWorkflowDefinitions(payload?.definitions);
        applyAuditSourceDisplayRules(payload?.sourceDisplayRules);
        setWorkflowConfigVersion((value) => value + 1);
      })
      .catch(() => {});
  }, []);
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [theme, setTheme] = useState(getInitialTheme);
  const [view, setView] = useState("home");
  const [lineageSelection, setLineageSelection] = useState(null);
  const [params, setParams] = useState({ path: "", ai: false, dbg: false, workflow: "hcyt", taskId: null });
  const [active, setActive] = useState("overview");
  const [railOpen, setRailOpen] = useState(false);
  const contentRef = useRef(null);
  const registry = useRef(new Map());

  const isFR = params.workflow === "fine-report";
  const isNups = params.workflow === "nups";
  const run = useAuditRun(view !== "home" ? params.taskId : null);
  const progressiveData = params.taskId
    ? mergePartialReport(EMPTY_AUDIT_REPORT, run.statusPayload, run.partialResult)
    : null;
  const liveData = run.report || progressiveData;
  const mockDataset = isNups ? NUPS_DATA : (isFR ? FINEREPORT_DATA : HCYT_DATA);
  const mockData = t.sampleState === "pass" ? mockDataset.PASS : mockDataset.FAIL;
  const data = liveData || mockData;
  const navList = isNups ? NUPS_NAV : (isFR ? FR_NAV : SECTION_NAV);
  const workflowName = WORKFLOWS.find((workflow) => workflow.key === params.workflow)?.name || params.workflow;
  const aiEnabled = Boolean(data?.ai) || (!params.taskId && (params.ai || t.showAi));
  const canShowRail = view === "results" && (!IS_API_MODE || !!liveData);
  const currentRevision = liveData?.task?.revision || run.task?.revision || (IS_API_MODE ? `task-${params.taskId || "pending"}` : data.task.revision);
  const projectsState = useAsyncResource(() => reviewService.getProjects(), [], { enabled: IS_API_MODE && view === "home" });
  const tasksState = useAsyncResource(() => reviewService.getAuditTasks(), [view], { enabled: IS_API_MODE && view === "home" });
  const auditResultsState = useAsyncResource(() => reviewService.getAuditResults(), [], {
    enabled: IS_API_MODE && view === "results" && !isFR && !params.taskId,
  });
  const fineReportItemsState = useAsyncResource(() => reviewService.getFineReportItems(), [], {
    enabled: IS_API_MODE && view === "results" && isFR && !params.taskId,
  });

  useEffect(() => {
    const root = document.documentElement;
    if (t.density === "standard") root.removeAttribute("data-density");
    else root.dataset.density = t.density;
    root.style.setProperty("--accent", t.accent);
  }, [t]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

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
      return await run.startAuditRun({
        sourceRef: payload.path,
        repo: payload.path,
        sourceType: payload.sourceType || "unknown",
        workflow: payload.workflow,
        type: payload.type,
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
    setRailOpen(false);
    contentRef.current?.scrollTo({ top: 0 });
  }

  const taskFailed = !!params.taskId && shouldShowAuditRunFailure(run.pageStatus, run.report);
  const isTaskStateView =
    !!params.taskId && (
      (IS_API_MODE && !!run.error && !liveData) ||
      taskFailed
    );

  const page = useMemo(() => {
    if (view === "home") {
      return (
        <Suspense fallback={<PageFallback />}>
          <HomePage
            onSubmit={submit}
            projectsState={projectsState}
            tasksState={tasksState}
            onCreateTask={handleCreateTask}
            dataMode={AUDIT_DATA_MODE}
            submitting={run.starting}
          />
        </Suspense>
      );
    }
    if (view === "lineage" && lineageSelection && params.taskId) {
      return (
        <Suspense fallback={<PageFallback />}>
          <LineagePage
            taskId={params.taskId}
            selection={lineageSelection}
            onBack={() => setView("results")}
          />
        </Suspense>
      );
    }
    if (IS_API_MODE && params.taskId && run.error && !liveData) {
      return <ApiErrorView error={run.error} onBack={() => setView("home")} />;
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
          onViewLineage={(script) => { setLineageSelection(script); setView("lineage"); }}
          lineageEnabled={Boolean(IS_API_MODE && params.taskId && run.report && data.pyScripts?.length)}
        />
      </Suspense>
    );
  }, [aiEnabled, auditResultsState, data, fineReportItemsState, isFR, isNups, lineageSelection, liveData, params.taskId, projectsState, run.error, run.running, run.task, t.variant, taskFailed, tasksState, view]);

  return (
    <div className={`app${canShowRail ? "" : " no-rail"}`}>
      {canShowRail ? (
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
          {view !== "home" ? (
            <>
              <button className="iconbtn mobile-menu-btn" title="导航菜单" onClick={() => setRailOpen((o) => !o)}>
                <Icon name="menu" size={16} />
              </button>
              <button className="btn ghost sm" onClick={() => view === "lineage" ? setView("results") : setView("home")}><Icon name="chevron" size={14} style={{ transform: "rotate(180deg)" }} /> {view === "lineage" ? "审查结果" : "新建审查"}</button>
              <div className="crumb">
                <span className="seg">{workflowName}</span>
                <span className="sep">/</span>
                <span className="seg cur mono">{currentRevision}</span>
                <span className="path">{params.path || data.task.repo}</span>
              </div>
            </>
          ) : (
            <div className="crumb"><span className="seg cur">首页 / 提交审查</span></div>
          )}
          <span className="topbar-spacer" />
          <ThemeToggle
            theme={theme}
            onToggle={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
          />
        </header>

        <div className={`content${isTaskStateView ? " content-task-state" : ""}`} ref={contentRef}>
          {view === "home"
            ? page
            : view === "lineage"
              ? <div className="content-inner">{page}</div>
            : isTaskStateView
              ? <div className="audit-running-main">{page}</div>
              : <div className="content-inner">{page}</div>}
        </div>

        <AppFooter />

      </div>

      {showTweakControls ? <TweaksPanel title="Tweaks">
        <TweakSection label="主题" />
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

