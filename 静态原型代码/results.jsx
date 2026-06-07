/* HCYT results page — status header, all check sections, layout variants. */

const STATUS_META = {
  pass: { tone: "ok", icon: "check", label: "审查通过", desc: "未发现阻断性问题，可合并" },
  fail: { tone: "err", icon: "x", label: "审查未通过", desc: "存在需修复的阻断性问题" },
  warn: { tone: "warn", icon: "alert", label: "审查通过（含警告）", desc: "存在建议修复的警告项" },
};

function StatusHeader({ d }) {
  const s = STATUS_META[d.task.status] || STATUS_META.warn;
  const t = d.task;
  return (
    <div className={"status-hero card " + s.tone} >
      <div className="sh-main">
        <div className={"sh-badge " + s.tone}><Icon name={s.icon} size={26} stroke={2.4} /></div>
        <div className="sh-text">
          <div className="sh-title-row">
            <h2 className="sh-title">{s.label}</h2>
            <Badge tone="accent" icon="db">{t.workflow}</Badge>
          </div>
          <p className="sh-desc">{s.desc}</p>
          <div className="sh-meta mono">
            <span><Icon name="branch" size={12} /> {t.revision}</span>
            <span className="sh-sep">·</span>
            <span>{t.author}</span>
            <span className="sh-sep">·</span>
            <span><Icon name="clock" size={12} /> {t.startedAt}</span>
            <span className="sh-sep">·</span>
            <span>耗时 {t.duration}</span>
          </div>
        </div>
      </div>
      <div className="metrics sh-metrics">
        <Metric label="变更文件" value={t.changedFiles} icon="file" />
        <Metric label="检查项" value={t.checks} icon="layers" />
        <Metric label="错误" value={t.errors} tone={t.errors ? "err" : "ok"} icon="x" />
        <Metric label="警告" value={t.warnings} tone={t.warnings ? "warn" : "ok"} icon="alert" />
        <Metric label="冲突" value={t.conflicts} tone={t.conflicts ? "err" : "ok"} icon="conflict" />
      </div>
    </div>
  );
}

function levelOf(rows) {
  if (!rows || !rows.length) return null;
  if (rows.some(r => r.level === "err")) return "err";
  if (rows.some(r => r.level === "warn")) return "warn";
  return "ok";
}

function ChangesSection({ d, reg }) {
  const counts = d.changes.reduce((a, c) => (a[c.type] = (a[c.type] || 0) + 1, a), {});
  return (
    <Panel id="changes" icon="git" title="SVN 变更文件列表" reg registerRef={reg}
      count={d.changes.length} countTone="info"
      right={<span className="diffstat" style={{ marginRight: 4 }}>
        <span className="add mono">A {counts.A || 0}</span>
        <span className="del mono" style={{ color: "var(--info-fg)" }}>M {counts.M || 0}</span>
      </span>}>
      <div className="panel-body flush">
        <div className="flist">
          {d.changes.map((c, i) => {
            const dir = c.path.slice(0, c.path.lastIndexOf("/") + 1);
            const name = c.path.slice(c.path.lastIndexOf("/") + 1);
            return (
              <div key={i} className="frow">
                <span className={"chg-tag " + c.type}>{c.type}</span>
                <span className="fpath"><span className="fdir">{dir}</span>{name}</span>
                <Badge>{c.cat}</Badge>
                <span className="diffstat">
                  <span className="add">+{c.add}</span>
                  <span className="del">−{c.del}</span>
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
  const has = d.conflicts.length > 0;
  return (
    <Panel id="conflict" icon="conflict" title="trunk 重叠冲突文件" reg registerRef={reg}
      count={d.conflicts.length} countTone={has ? "err" : "ok"} defaultOpen={has}
      sub={has ? "与主干内容存在重叠" : null}>
      <div className="panel-body">
        {has ? (
          <div className="flist conflict-list">
            {d.conflicts.map((c, i) => (
              <div key={i} className="frow conflict" style={{ height: "auto", padding: "10px 12px" }}>
                <Icon name="conflict" size={15} style={{ color: "var(--err)", flex: "none" }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="fpath" style={{ color: "var(--err-fg)" }}>{c.path}</div>
                  <div style={{ fontSize: "var(--fs-xs)", color: "var(--text-2)", marginTop: 3 }}>{c.note}</div>
                </div>
                <div className="diffstat" style={{ flexDirection: "column", gap: 2, textAlign: "right" }}>
                  <span className="mono" style={{ color: "var(--text-3)" }}>trunk {c.trunkRev}</span>
                  <span className="mono" style={{ color: "var(--err-fg)" }}>本次 {c.mineRev}</span>
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
  const lv = levelOf(rows);
  const errs = rows.filter(r => r.level === "err").length;
  const warns = rows.filter(r => r.level === "warn").length;
  return (
    <Panel id={id} icon={icon} title={title} reg registerRef={reg}
      count={rows.length || "通过"} countTone={lv || "ok"} defaultOpen={rows.length > 0}
      right={rows.length ? (
        <span className="mini-counts">
          {errs ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{errs}</span> : null}
          {warns ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{warns}</span> : null}
        </span>
      ) : null}>
      <div className={rows.length ? "panel-body flush" : "panel-body"}>
        {rows.length ? <ViolationTable rows={rows} /> : <OkState>{okMsg || "未发现违规项"}</OkState>}
      </div>
    </Panel>
  );
}

function ScheduleSection({ d, reg }) {
  const s = d.schedule;
  const lv = levelOf(s.rows);
  const cols = [
    { key: "table", label: "表" },
    { key: "item", label: "对象", cls: "rule-cell" },
    { key: "rule", label: "规则" },
    { key: "level", label: "级别" },
    { key: "msg", label: "说明" },
  ];
  return (
    <Panel id="schedule" icon="grid" title="调度表检查（Excel）" reg registerRef={reg}
      count={s.cycles ? "循环依赖" : (lv === "ok" ? "通过" : s.rows.length)} countTone={s.cycles ? "err" : (lv || "ok")}
      defaultOpen={lv !== "ok"}>
      <div className="panel-body">
        <div className="metrics" style={{ marginBottom: "var(--gap)" }}>
          <Metric label="PLAN" value={s.summary.plan} />
          <Metric label="SEQ" value={s.summary.seq} />
          <Metric label="JOB" value={s.summary.job} />
          <Metric label="循环依赖" value={s.summary.cycles} tone={s.summary.cycles ? "err" : "ok"} />
          <Metric label="缺失映射" value={s.summary.missing} tone={s.summary.missing ? "warn" : "ok"} />
        </div>
        <div className="table-wrap" style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
          <table className="tbl">
            <thead><tr>{cols.map(c => <th key={c.key}>{c.label}</th>)}</tr></thead>
            <tbody>
              {s.rows.map((r, i) => (
                <tr key={i} className={r.level === "err" ? "err-row" : r.level === "warn" ? "warn-row" : ""}>
                  <td><Badge mono tone={r.table === "PLAN" ? "accent" : r.table === "SEQ" ? "info" : ""}>{r.table}</Badge></td>
                  <td className="rule-cell mono" style={{ fontSize: "var(--fs-xs)" }}>{r.item}</td>
                  <td>{r.rule}</td>
                  <td><Sev level={r.level} /></td>
                  <td>{r.msg}</td>
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
  { key: "src", label: "源表 / 贴源", cls: "src" },
  { key: "temp", label: "临时表", cls: "temp" },
];

function RefTablesSection({ d, reg }) {
  return (
    <Panel id="reftables" icon="db" title="SQL 引用表汇总" reg registerRef={reg}
      count={d.refTables.length} sub="去重后按类型着色">
      <div className="panel-body">
        <div className="legend" style={{ marginBottom: 14 }}>
          {REF_TYPES.map(t => {
            const n = d.refTables.filter(r => r.type === t.key).length;
            return <span key={t.key} className="lg-item"><span className={"chip " + t.cls}><span className="cdot" />{t.label}</span><span className="mono" style={{ color: "var(--text-3)" }}>×{n}</span></span>;
          })}
        </div>
        {REF_TYPES.map(t => {
          const items = d.refTables.filter(r => r.type === t.key);
          if (!items.length) return null;
          return (
            <div key={t.key} style={{ marginBottom: 12 }}>
              <div className="subhead" style={{ marginBottom: 7 }}>{t.label} · {items.length}</div>
              <div className="chips">
                {items.map((r, i) => <span key={i} className={"chip " + t.cls}><span className="cdot" />{r.name}</span>)}
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
    <Panel id="deps" icon="flow" title="作业依赖分析" reg registerRef={reg} sub="上下游依赖关系">
      <div className="panel-body">
        <div className="dep-graph">
          {d.deps.map((lane, i) => (
            <div key={i} className="dep-lane">
              <div className="dep-lane-label">{lane.lane}</div>
              <div className="dep-nodes">
                {lane.nodes.map((n, j) => (
                  <span key={j} className={"dep-node" + (n.focus ? " focus" : "")}>
                    <Icon name={n.focus ? "play" : "db"} size={11} />
                    {n.name}{n.q ? <span className="nq">{n.q}</span> : null}
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

function AiSection({ d, reg }) {
  const a = d.ai;
  const tone = a.verdict === "ok" ? "ok" : a.verdict === "err" ? "err" : "warn";
  return (
    <Panel id="ai" icon="sparkle" title="AI 分析" reg registerRef={reg}
      sub={a.model} right={<Badge tone={tone} icon={tone === "ok" ? "check" : "alert"}>{a.verdict === "ok" ? "建议合并" : "建议修复"}</Badge>}>
      <div className="panel-body ai-body">
        <div className="ai-summary">
          <span className="ai-spark"><Icon name="sparkle" size={15} /></span>
          <p>{a.summary}</p>
        </div>
        <div className="ai-findings">
          {a.findings.map((f, i) => (
            <div key={i} className={"ai-finding " + f.sev}>
              <Sev level={f.sev} />
              <div className="aif-body">
                <div className="aif-title">{f.title}</div>
                <div className="aif-text">{f.body}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}

/* ---- aggregated issues table (for "issues-first" variant) ---- */
function aggregateIssues(d) {
  const groups = [
    ["DWS SQL", d.dws], ["Hive SQL", d.hive], ["Python", d.python],
    ["后置脚本", d.sbin], ["配置文件", d.config], ["收卸配置", d.recv],
    ["调度表", d.schedule.rows.filter(r => r.level !== "ok")],
  ];
  const out = [];
  for (const [cat, rows] of groups) for (const r of rows) out.push({ cat, ...r });
  const order = { err: 0, warn: 1, info: 2, ok: 3 };
  return out.sort((a, b) => order[a.level] - order[b.level]);
}

function IssuesBoard({ d }) {
  const issues = aggregateIssues(d);
  if (!issues.length) return (
    <div className="card" style={{ padding: 20, marginBottom: "var(--gap)" }}>
      <OkState>所有检查项均已通过，未发现需要修复的问题</OkState>
    </div>
  );
  return (
    <div className="card issues-board" style={{ marginBottom: "var(--gap)", overflow: "hidden" }}>
      <div className="ib-head"><Icon name="search" size={14} /> 问题汇总 · 按严重级别排序 <Badge tone="err" mono>{issues.filter(i => i.level === "err").length} 错误</Badge> <Badge tone="warn" mono>{issues.filter(i => i.level === "warn").length} 警告</Badge></div>
      <div className="table-wrap">
        <table className="tbl">
          <thead><tr><th>级别</th><th>分类</th><th>规则</th><th>位置</th><th>说明</th></tr></thead>
          <tbody>
            {issues.map((r, i) => (
              <tr key={i} className={r.level === "err" ? "err-row" : "warn-row"}>
                <td><Sev level={r.level} /></td>
                <td><Badge>{r.cat}</Badge></td>
                <td className="rule-cell">{r.rule}</td>
                <td className="mono" style={{ fontSize: "var(--fs-xs)" }}>{r.file ? r.file + (r.line ? ":" + r.line : "") : r.item}</td>
                <td>{r.msg}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ---- category status board (for "board" variant) ---- */
const CATS = [
  { id: "conflict", label: "trunk 冲突", icon: "conflict", get: d => d.conflicts },
  { id: "dws", label: "DWS SQL", icon: "db", get: d => d.dws },
  { id: "hive", label: "Hive SQL", icon: "db", get: d => d.hive },
  { id: "python", label: "Python 脚本", icon: "python", get: d => d.python },
  { id: "sbin", label: "后置脚本", icon: "terminal", get: d => d.sbin },
  { id: "config", label: "配置文件", icon: "cog", get: d => d.config },
  { id: "recv", label: "收卸配置", icon: "download", get: d => d.recv },
  { id: "schedule", label: "调度表", icon: "grid", get: d => d.schedule.rows.filter(r => r.level !== "ok") },
];

function CategoryBoard({ d, onJump }) {
  return (
    <div className="cat-board">
      {CATS.map(c => {
        const rows = c.get(d);
        const lv = levelOf(rows) || "ok";
        return (
          <div key={c.id} className={"cat-card " + lv} onClick={() => onJump && onJump(c.id)}>
            <div className="cc-top">
              <span className="cc-ico"><Icon name={c.icon} size={15} /></span>
              <Dot tone={lv} />
            </div>
            <div className="cc-label">{c.label}</div>
            <div className="cc-stat mono">{rows.length ? rows.length + " 项" : "通过"}</div>
          </div>
        );
      })}
    </div>
  );
}

function ResultsPage({ d, aiEnabled, variant, reg, onJump }) {
  const [openScript, setOpenScript] = React.useState(null);
  return (
    <div className="results-page fade-in">
      {variant !== "issues" ? <StatusHeader d={d} /> : null}
      {variant === "board" ? (
        <div className="card" style={{ padding: "var(--pad-card)", marginBottom: "var(--gap)" }}>
          <div className="subhead"><Icon name="grid" size={12} /> 检查项概览</div>
          <CategoryBoard d={d} onJump={onJump} />
        </div>
      ) : null}
      {variant === "issues" ? <><StatusHeader d={d} /><IssuesBoard d={d} /></> : null}

      <ChangesSection d={d} reg={reg} />
      <ConflictSection d={d} reg={reg} />
      <CheckSection id="dws" icon="db" title="DWS SQL 检查结果" rows={d.dws} reg={reg} />
      <CheckSection id="hive" icon="db" title="Hive SQL 检查结果" rows={d.hive} reg={reg} />
      <PyScriptAuditSection d={d} reg={reg} onOpen={setOpenScript} />
      <CheckSection id="sbin" icon="terminal" title="后置脚本检查（sbin）" rows={d.sbin} reg={reg} />
      <CheckSection id="config" icon="cog" title="配置文件检查" rows={d.config} reg={reg} okMsg="Schema 配置文件校验通过" />
      <CheckSection id="recv" icon="download" title="收卸配置检查" rows={d.recv} reg={reg} okMsg="recv_json 配置校验通过" />
      <ScheduleSection d={d} reg={reg} />
      <RefTablesSection d={d} reg={reg} />
      <DepsSection d={d} reg={reg} />
      {aiEnabled ? <AiSection d={d} reg={reg} /> : null}
      {openScript ? <ScriptDetailDrawer script={openScript} onClose={() => setOpenScript(null)} /> : null}
    </div>
  );
}

Object.assign(window, { ResultsPage, CATS, STATUS_META, levelOf, AiSection });
