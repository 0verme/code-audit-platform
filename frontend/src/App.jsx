import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import { ResultRail } from "./components/app/ResultRail";
import {
  ApiErrorView as TaskApiErrorView,
  FailedView as TaskFailedView,
  PageFallback as TaskPageFallback,
} from "./components/app/TaskStateViews";
import { Icon } from "./components/ui";
import { TweakColor, TweaksPanel, TweakRadio, TweakSection, TweakToggle, useTweaks } from "./components/tweaksPanel";
import { AUDIT_DATA_MODE, IS_API_MODE } from "./config/api";
import { applyBackendWorkflowDefinitions } from "./config/auditWorkflows";
import { applyAuditSourceDisplayRules } from "./config/auditSourceDisplayConfig";
import { APP_EDITION, APP_NAME, APP_VERSION } from "./config/appMeta";
import { getResultNavigation } from "./config/resultNavigation";
import { useAsyncResource } from "./hooks/useAsyncResource";
import { mergePartialReport, shouldShowAuditRunFailure, useAuditRun } from "./hooks/useAuditRun";
import { FINEREPORT_DATA, HCYT_DATA, NUPS_DATA, WORKFLOWS } from "./mock/data";
import { reviewService } from "./services/reviewService";
import { getReportKey } from "./utils/fineReportPresentation";
import { getScriptKey } from "./utils/scriptAuditPresentation";

const HomePage = lazy(() => import("./pages/HomePage"));
const ResultsPage = lazy(() => import("./pages/ResultsPage").then((module) => ({ default: module.ResultsPage })));
const FineReportResultsPage = lazy(() => import("./pages/FineReportPage").then((module) => ({ default: module.FineReportResultsPage })));
const NupsResultsPage = lazy(() => import("./pages/NupsPage").then((module) => ({ default: module.NupsResultsPage })));
const LineagePage = lazy(() => import("./pages/LineagePage").then((module) => ({ default: module.LineagePage })));
const PublishListPage = lazy(() => import("./pages/PublishListPage"));
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
  const [activeScriptKey, setActiveScriptKey] = useState("");
  const [activeReportKey, setActiveReportKey] = useState("");
  const [scriptJumpRequest, setScriptJumpRequest] = useState(null);
  const [reportJumpRequest, setReportJumpRequest] = useState(null);
  const scriptJumpSequence = useRef(0);
  const reportJumpSequence = useRef(0);
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
  const navList = getResultNavigation(params.workflow);
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
    setActiveScriptKey("");
    setActiveReportKey("");
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

  function jumpToScript(script) {
    const scriptKey = getScriptKey(script);
    jump("python");
    if (!scriptKey) return;
    setActiveScriptKey(scriptKey);
    scriptJumpSequence.current += 1;
    setScriptJumpRequest({ key: scriptKey, sequence: scriptJumpSequence.current });
  }

  function jumpToReport(report) {
    const reportKey = getReportKey(report);
    jump("reports");
    if (!reportKey) return;
    setActiveReportKey(reportKey);
    reportJumpSequence.current += 1;
    setReportJumpRequest({ key: reportKey, sequence: reportJumpSequence.current });
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
      if (current !== "python") setActiveScriptKey("");
      if (current !== "reports") setActiveReportKey("");
    };
    container.addEventListener("scroll", onScroll, { passive: true });
    return () => container.removeEventListener("scroll", onScroll);
  }, [navList, view]);

  const { startAuditRun } = run;
  const handleCreateTask = useMemo(
    () => async (payload) => {
      try {
        return await startAuditRun({
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
    },
    [startAuditRun],
  );

  function submit(nextParams) {
    setParams({ taskId: null, ...nextParams });
    setView("results");
    setActive("overview");
    setActiveScriptKey("");
    setActiveReportKey("");
    setScriptJumpRequest(null);
    setReportJumpRequest(null);
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
    if (view === "publish") {
      return <Suspense fallback={<TaskPageFallback />}><PublishListPage /></Suspense>;
    }
    if (view === "home") {
      return (
        <Suspense fallback={<TaskPageFallback />}>
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
        <Suspense fallback={<TaskPageFallback />}>
          <LineagePage
            taskId={params.taskId}
            selection={lineageSelection}
            onBack={() => setView("results")}
          />
        </Suspense>
      );
    }
    if (IS_API_MODE && params.taskId && run.error && !liveData) {
      return <TaskApiErrorView error={run.error} onBack={() => setView("home")} />;
    }
    if (taskFailed) {
      return <TaskFailedView task={run.task} onBack={() => setView("home")} />;
    }
    if (isNups) {
      return (
        <Suspense fallback={<TaskPageFallback />}>
          <NupsResultsPage d={data} aiEnabled={aiEnabled} reg={reg} onJump={jump} />
        </Suspense>
      );
    }
    if (isFR) {
      return (
        <Suspense fallback={<TaskPageFallback />}>
          <FineReportResultsPage
            d={data}
            aiEnabled={aiEnabled}
            reg={reg}
            apiState={liveData ? null : fineReportItemsState}
            reportDataPending={Boolean(params.taskId && run.running && !run.report)}
            reportJumpRequest={reportJumpRequest}
          />
        </Suspense>
      );
    }
    return (
      <Suspense fallback={<TaskPageFallback />}>
        <ResultsPage
          d={data}
          aiEnabled={aiEnabled}
          variant={t.variant}
          reg={reg}
          onJump={jump}
          apiState={liveData ? null : auditResultsState}
          onViewLineage={(script) => { setLineageSelection(script); setView("lineage"); }}
          lineageEnabled={Boolean(IS_API_MODE && params.taskId && run.report && data.pyScripts?.length)}
          scriptJumpRequest={scriptJumpRequest}
        />
      </Suspense>
    );
  }, [aiEnabled, auditResultsState, data, fineReportItemsState, handleCreateTask, isFR, isNups, lineageSelection, liveData, params.taskId, projectsState, reportJumpRequest, run.error, run.report, run.running, run.starting, run.task, scriptJumpRequest, t.variant, taskFailed, tasksState, view]);

  return (
    <div className={`app${canShowRail ? "" : " no-rail"}`}>
      {canShowRail ? (
        <>
          <div
            className={`rail-overlay${railOpen ? " shown" : ""}`}
            onClick={() => setRailOpen(false)}
          />
          <ResultRail
            data={data}
            active={active}
            activeScriptKey={activeScriptKey}
            activeReportKey={activeReportKey}
            onJump={(id) => { jump(id); setRailOpen(false); }}
            onJumpScript={(script) => { jumpToScript(script); setRailOpen(false); }}
            onJumpReport={(report) => { jumpToReport(report); setRailOpen(false); }}
            params={params}
            nav={navList}
            mobileOpen={railOpen}
          />
        </>
      ) : null}
      <div className="main">
        <header className="topbar">
          {view === "publish" ? (
            <>
              <button className="btn ghost sm" onClick={() => setView("home")}><Icon name="chevron" size={14} style={{ transform: "rotate(180deg)" }} /> 提交审查</button>
              <div className="crumb"><span className="seg cur">首页 / 当日上线清单</span></div>
            </>
          ) : view !== "home" ? (
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
          {view !== "publish" ? <button className="btn ghost sm" onClick={() => setView("publish")}><Icon name="calendar" size={14} /> 当日上线</button> : null}
          <ThemeToggle
            theme={theme}
            onToggle={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
          />
        </header>

        <div className={`content${isTaskStateView ? " content-task-state" : ""}`} ref={contentRef}>
          {view === "home" || view === "publish"
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

