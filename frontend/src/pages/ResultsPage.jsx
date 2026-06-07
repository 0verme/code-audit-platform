import { useMemo, useState } from "react";
import { Badge, Dot, Icon, levelOf, Metric, OkState, Panel, Sev, ViolationTable } from "../components/ui";
import { PyScriptAuditSection, ScriptDetailDrawer } from "./ScriptAudit";

export const STATUS_META = {
  pass: { tone: "ok", icon: "check", label: "审查通过", desc: "未发现阻断性问题，可合并" },
  fail: { tone: "err", icon: "x", label: "审查未通过", desc: "存在需要修复的阻断性问题" },
  warn: { tone: "warn", icon: "alert", label: "审查通过（含警告）", desc: "存在建议修复的告警项" },
};

export const SECTION_NAV = [
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

function StatusHeader({ d }) {
  const status = STATUS_META[d.task.status] || STATUS_META.warn;
  const task = d.task;
  return (
    <div className={`status-hero card ${status.tone}`}>
      <div className="sh-main">
        <div className={`sh-badge ${status.tone}`}><Icon name={status.icon} size={26} stroke={2.4} /></div>
        <div className="sh-text">
          <div className="sh-title-row">
            <h2 className="sh-title">{status.label}</h2>
            <Badge tone="accent" icon="db">{task.workflow}</Badge>
          </div>
          <p className="sh-desc">{status.desc}</p>
          <div className="sh-meta mono">
            <span><Icon name="branch" size={12} /> {task.revision}</span>
            <span className="sh-sep">/</span>
            <span>{task.author}</span>
            <span className="sh-sep">/</span>
            <span><Icon name="clock" size={12} /> {task.startedAt}</span>
            <span className="sh-sep">/</span>
            <span>耗时 {task.duration}</span>
          </div>
        </div>
      </div>
      <div className="metrics sh-metrics">
        <Metric label="变更文件" value={task.changedFiles} icon="file" />
        <Metric label="检查项" value={task.checks} icon="layers" />
        <Metric label="错误" value={task.errors} tone={task.errors ? "err" : "ok"} icon="x" />
        <Metric label="警告" value={task.warnings} tone={task.warnings ? "warn" : "ok"} icon="alert" />
        <Metric label="冲突" value={task.conflicts} tone={task.conflicts ? "err" : "ok"} icon="conflict" />
      </div>
    </div>
  );
}

function ChangesSection({ d, reg }) {
  const counts = d.changes.reduce((accumulator, item) => {
    accumulator[item.type] = (accumulator[item.type] || 0) + 1;
    return accumulator;
  }, {});

  return (
    <Panel
      id="changes"
      icon="git"
      title="SVN 变更文件列表"
      registerRef={reg}
      count={d.changes.length}
      countTone="info"
      right={
        <span className="diffstat" style={{ marginRight: 4 }}>
          <span className="add mono">A {counts.A || 0}</span>
          <span className="del mono" style={{ color: "var(--info-fg)" }}>M {counts.M || 0}</span>
        </span>
      }
    >
      <div className="panel-body flush">
        <div className="flist">
          {d.changes.map((change) => {
            const index = change.path.lastIndexOf("/") + 1;
            const dir = change.path.slice(0, index);
            const name = change.path.slice(index);
            return (
              <div key={change.path} className="frow">
                <span className={`chg-tag ${change.type}`}>{change.type}</span>
                <span className="fpath"><span className="fdir">{dir}</span>{name}</span>
                <Badge>{change.cat}</Badge>
                <span className="diffstat">
                  <span className="add">+{change.add}</span>
                  <span className="del">-{change.del}</span>
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </Panel>
  );
}

function ConflictSection({ d, reg }) {
  const hasConflicts = d.conflicts.length > 0;
  return (
    <Panel
      id="conflict"
      icon="conflict"
      title="trunk 重叠冲突文件"
      registerRef={reg}
      count={d.conflicts.length}
      countTone={hasConflicts ? "err" : "ok"}
      defaultOpen={hasConflicts}
      sub={hasConflicts ? "与主干内容存在重叠" : null}
    >
      <div className="panel-body">
        {hasConflicts ? (
          <div className="flist conflict-list">
            {d.conflicts.map((conflict) => (
              <div key={conflict.path} className="frow conflict" style={{ height: "auto", padding: "10px 12px" }}>
                <Icon name="conflict" size={15} style={{ color: "var(--err)", flex: "none" }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="fpath" style={{ color: "var(--err-fg)" }}>{conflict.path}</div>
                  <div style={{ fontSize: "var(--fs-xs)", color: "var(--text-2)", marginTop: 3 }}>{conflict.note}</div>
                </div>
                <div className="diffstat" style={{ flexDirection: "column", gap: 2, textAlign: "right" }}>
                  <span className="mono" style={{ color: "var(--text-3)" }}>trunk {conflict.trunkRev}</span>
                  <span className="mono" style={{ color: "var(--err-fg)" }}>本次 {conflict.mineRev}</span>
                </div>
              </div>
            ))}
          </div>
        ) : <OkState>未检测到与 trunk 主干的重叠冲突</OkState>}
      </div>
    </Panel>
  );
}

function CheckSection({ id, icon, title, rows, reg, okMsg }) {
  const severity = levelOf(rows);
  const errs = rows.filter((row) => row.level === "err").length;
  const warns = rows.filter((row) => row.level === "warn").length;

  return (
    <Panel
      id={id}
      icon={icon}
      title={title}
      registerRef={reg}
      count={rows.length || "通过"}
      countTone={severity || "ok"}
      defaultOpen={rows.length > 0}
      right={
        rows.length ? (
          <span className="mini-counts">
            {errs ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{errs}</span> : null}
            {warns ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{warns}</span> : null}
          </span>
        ) : null
      }
    >
      <div className={rows.length ? "panel-body flush" : "panel-body"}>
        {rows.length ? <ViolationTable rows={rows} /> : <OkState>{okMsg || "未发现违规项"}</OkState>}
      </div>
    </Panel>
  );
}

function ScheduleSection({ d, reg }) {
  const schedule = d.schedule;
  const severity = levelOf(schedule.rows);
  const columns = [
    { key: "table", label: "表" },
    { key: "item", label: "对象", cls: "rule-cell" },
    { key: "rule", label: "规则" },
    { key: "level", label: "级别" },
    { key: "msg", label: "说明" },
  ];

  return (
    <Panel
      id="schedule"
      icon="grid"
      title="调度表检查（Excel）"
      registerRef={reg}
      count={schedule.summary.cycles ? "循环依赖" : (severity === "ok" ? "通过" : schedule.rows.length)}
      countTone={schedule.summary.cycles ? "err" : (severity || "ok")}
      defaultOpen={severity !== "ok"}
    >
      <div className="panel-body">
        <div className="metrics" style={{ marginBottom: "var(--gap)" }}>
          <Metric label="PLAN" value={schedule.summary.plan} />
          <Metric label="SEQ" value={schedule.summary.seq} />
          <Metric label="JOB" value={schedule.summary.job} />
          <Metric label="循环依赖" value={schedule.summary.cycles} tone={schedule.summary.cycles ? "err" : "ok"} />
          <Metric label="缺失映射" value={schedule.summary.missing} tone={schedule.summary.missing ? "warn" : "ok"} />
        </div>
        <div className="table-wrap" style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
          <table className="tbl">
            <thead><tr>{columns.map((column) => <th key={column.key}>{column.label}</th>)}</tr></thead>
            <tbody>
              {schedule.rows.map((row, index) => (
                <tr key={index} className={row.level === "err" ? "err-row" : row.level === "warn" ? "warn-row" : ""}>
                  <td><Badge mono tone={row.table === "PLAN" ? "accent" : row.table === "SEQ" ? "info" : ""}>{row.table}</Badge></td>
                  <td className="rule-cell mono" style={{ fontSize: "var(--fs-xs)" }}>{row.item}</td>
                  <td>{row.rule}</td>
                  <td><Sev level={row.level} /></td>
                  <td>{row.msg}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Panel>
  );
}

const REF_TYPES = [
  { key: "result", label: "结果表", cls: "result" },
  { key: "mid", label: "中间表", cls: "mid" },
  { key: "src", label: "源表 / 维表", cls: "src" },
  { key: "temp", label: "临时表", cls: "temp" },
];

function RefTablesSection({ d, reg }) {
  return (
    <Panel id="reftables" icon="db" title="SQL 引用表汇总" registerRef={reg} count={d.refTables.length} sub="去重后按类型着色">
      <div className="panel-body">
        <div className="legend" style={{ marginBottom: 14 }}>
          {REF_TYPES.map((type) => {
            const count = d.refTables.filter((item) => item.type === type.key).length;
            return (
              <span key={type.key} className="lg-item">
                <span className={`chip ${type.cls}`}><span className="cdot" />{type.label}</span>
                <span className="mono" style={{ color: "var(--text-3)" }}>x{count}</span>
              </span>
            );
          })}
        </div>
        {REF_TYPES.map((type) => {
          const items = d.refTables.filter((item) => item.type === type.key);
          if (!items.length) return null;
          return (
            <div key={type.key} style={{ marginBottom: 12 }}>
              <div className="subhead" style={{ marginBottom: 7 }}>{type.label} / {items.length}</div>
              <div className="chips">
                {items.map((item) => <span key={item.name} className={`chip ${type.cls}`}><span className="cdot" />{item.name}</span>)}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function DepsSection({ d, reg }) {
  return (
    <Panel id="deps" icon="flow" title="作业依赖分析" registerRef={reg} sub="上下游依赖关系">
      <div className="panel-body">
        <div className="dep-graph">
          {d.deps.map((lane) => (
            <div key={lane.lane} className="dep-lane">
              <div className="dep-lane-label">{lane.lane}</div>
              <div className="dep-nodes">
                {lane.nodes.map((node) => (
                  <span key={node.name} className={`dep-node${node.focus ? " focus" : ""}`}>
                    <Icon name={node.focus ? "play" : "db"} size={11} />
                    {node.name}
                    {node.q ? <span className="nq">{node.q}</span> : null}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}

export function AiSection({ d, reg }) {
  const ai = d.ai;
  const tone = ai.verdict === "ok" ? "ok" : ai.verdict === "err" ? "err" : "warn";
  return (
    <Panel
      id="ai"
      icon="sparkle"
      title="AI 分析"
      registerRef={reg}
      sub={ai.model}
      right={<Badge tone={tone} icon={tone === "ok" ? "check" : "alert"}>{ai.verdict === "ok" ? "建议合并" : "建议修复"}</Badge>}
    >
      <div className="panel-body ai-body">
        <div className="ai-summary">
          <span className="ai-spark"><Icon name="sparkle" size={15} /></span>
          <p>{ai.summary}</p>
        </div>
        <div className="ai-findings">
          {ai.findings.map((finding, index) => (
            <div key={index} className={`ai-finding ${finding.sev}`}>
              <Sev level={finding.sev} />
              <div className="aif-body">
                <div className="aif-title">{finding.title}</div>
                <div className="aif-text">{finding.body}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}

function aggregateIssues(data) {
  const groups = [
    ["DWS SQL", data.dws],
    ["Hive SQL", data.hive],
    ["Python", data.python],
    ["后置脚本", data.sbin],
    ["配置文件", data.config],
    ["收卸配置", data.recv],
    ["调度表", data.schedule.rows.filter((row) => row.level !== "ok")],
  ];
  const order = { err: 0, warn: 1, info: 2, ok: 3 };
  return groups.flatMap(([cat, rows]) => rows.map((row) => ({ cat, ...row }))).sort((left, right) => order[left.level] - order[right.level]);
}

function IssuesBoard({ d }) {
  const issues = aggregateIssues(d);
  if (!issues.length) {
    return (
      <div className="card" style={{ padding: 20, marginBottom: "var(--gap)" }}>
        <OkState>所有检查项均已通过，未发现需要修复的问题</OkState>
      </div>
    );
  }
  return (
    <div className="card issues-board" style={{ marginBottom: "var(--gap)", overflow: "hidden" }}>
      <div className="ib-head"><Icon name="search" size={14} /> 问题汇总 / 按严重级别排序 <Badge tone="err" mono>{issues.filter((item) => item.level === "err").length} 错误</Badge> <Badge tone="warn" mono>{issues.filter((item) => item.level === "warn").length} 警告</Badge></div>
      <div className="table-wrap">
        <table className="tbl">
          <thead><tr><th>级别</th><th>分类</th><th>规则</th><th>位置</th><th>说明</th></tr></thead>
          <tbody>
            {issues.map((item, index) => (
              <tr key={index} className={item.level === "err" ? "err-row" : "warn-row"}>
                <td><Sev level={item.level} /></td>
                <td><Badge>{item.cat}</Badge></td>
                <td className="rule-cell">{item.rule}</td>
                <td className="mono" style={{ fontSize: "var(--fs-xs)" }}>{item.file ? `${item.file}${item.line ? `:${item.line}` : ""}` : item.item}</td>
                <td>{item.msg}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const CATS = [
  { id: "conflict", label: "trunk 冲突", icon: "conflict", get: (data) => data.conflicts },
  { id: "dws", label: "DWS SQL", icon: "db", get: (data) => data.dws },
  { id: "hive", label: "Hive SQL", icon: "db", get: (data) => data.hive },
  { id: "python", label: "Python 脚本", icon: "python", get: (data) => data.python },
  { id: "sbin", label: "后置脚本", icon: "terminal", get: (data) => data.sbin },
  { id: "config", label: "配置文件", icon: "cog", get: (data) => data.config },
  { id: "recv", label: "收卸配置", icon: "download", get: (data) => data.recv },
  { id: "schedule", label: "调度表", icon: "grid", get: (data) => data.schedule.rows.filter((row) => row.level !== "ok") },
];

function CategoryBoard({ d, onJump }) {
  return (
    <div className="cat-board">
      {CATS.map((category) => {
        const rows = category.get(d);
        const severity = levelOf(rows) || "ok";
        return (
          <div key={category.id} className={`cat-card ${severity}`} onClick={() => onJump(category.id)}>
            <div className="cc-top">
              <span className="cc-ico"><Icon name={category.icon} size={15} /></span>
              <Dot tone={severity} />
            </div>
            <div className="cc-label">{category.label}</div>
            <div className="cc-stat mono">{rows.length ? `${rows.length} 项` : "通过"}</div>
          </div>
        );
      })}
    </div>
  );
}

export function mergeAuditResults(baseData, apiRows) {
  if (!apiRows?.length) return baseData;
  const grouped = {
    dws: [],
    hive: [],
    python: [],
    sbin: [],
    config: [],
    recv: [],
  };

  apiRows.forEach((row) => {
    const normalized = {
      file: row.file_name,
      line: row.line_no,
      rule: row.rule_name,
      level: row.level,
      msg: row.message,
    };
    if (row.category in grouped) {
      grouped[row.category].push(normalized);
    }
  });

  const totalErrors = Object.values(grouped).flat().filter((row) => row.level === "err").length;
  const totalWarnings = Object.values(grouped).flat().filter((row) => row.level === "warn").length;

  return {
    ...baseData,
    task: {
      ...baseData.task,
      errors: totalErrors,
      warnings: totalWarnings,
      status: totalErrors ? "fail" : totalWarnings ? "warn" : "pass",
    },
    ...Object.fromEntries(Object.entries(grouped).map(([key, value]) => [key, value.length ? value : baseData[key]])),
  };
}

export function ResultsPage({ d, aiEnabled, variant, reg, onJump, apiState }) {
  const [openScript, setOpenScript] = useState(null);
  const mergedData = useMemo(() => mergeAuditResults(d, apiState?.data), [d, apiState?.data]);

  return (
    <div className="results-page fade-in">
      {apiState?.loading ? <div className="card" style={{ padding: 14, marginBottom: "var(--gap)" }}>正在加载审查结果...</div> : null}
      {apiState?.error ? <div className="card" style={{ padding: 14, marginBottom: "var(--gap)", borderColor: "var(--warn)" }}>审查结果接口不可用，已回退到本地 mock 数据。</div> : null}
      {variant !== "issues" ? <StatusHeader d={mergedData} /> : null}
      {variant === "board" ? (
        <div className="card" style={{ padding: "var(--pad-card)", marginBottom: "var(--gap)" }}>
          <div className="subhead"><Icon name="grid" size={12} /> 检查项概览</div>
          <CategoryBoard d={mergedData} onJump={onJump} />
        </div>
      ) : null}
      {variant === "issues" ? <><StatusHeader d={mergedData} /><IssuesBoard d={mergedData} /></> : null}
      <ChangesSection d={mergedData} reg={reg} />
      <ConflictSection d={mergedData} reg={reg} />
      <CheckSection id="dws" icon="db" title="DWS SQL 检查结果" rows={mergedData.dws} reg={reg} />
      <CheckSection id="hive" icon="db" title="Hive SQL 检查结果" rows={mergedData.hive} reg={reg} />
      <PyScriptAuditSection d={mergedData} reg={reg} onOpen={setOpenScript} />
      <CheckSection id="sbin" icon="terminal" title="后置脚本检查（sbin）" rows={mergedData.sbin} reg={reg} />
      <CheckSection id="config" icon="cog" title="配置文件检查" rows={mergedData.config} reg={reg} okMsg="Schema 配置文件校验通过" />
      <CheckSection id="recv" icon="download" title="收卸配置检查" rows={mergedData.recv} reg={reg} okMsg="recv_json 配置校验通过" />
      <ScheduleSection d={mergedData} reg={reg} />
      <RefTablesSection d={mergedData} reg={reg} />
      <DepsSection d={mergedData} reg={reg} />
      {aiEnabled ? <AiSection d={mergedData} reg={reg} /> : null}
      {openScript ? <ScriptDetailDrawer script={openScript} onClose={() => setOpenScript(null)} /> : null}
    </div>
  );
}
