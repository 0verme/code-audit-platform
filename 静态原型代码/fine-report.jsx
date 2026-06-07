/* FineReport 报表审查 — 按报表列表检查。
   Flat report list (.cpt / .frm) → per-report 审核重点 + 逐项问题表 drawer. */

/* extra glyphs for FineReport dimensions */
Object.assign(window.Ic, {
  gauge: <><path d="M12 13l4.5-4.5" /><path d="M4 19a8 8 0 1 1 16 0" /><circle cx="12" cy="13" r="1.3" /></>,
  shield: <path d="M12 3l8 3v5.5c0 4.6-3.2 7.7-8 9.2-4.8-1.5-8-4.6-8-9.2V6z" />,
  screen: <><rect x="3" y="4" width="18" height="13" rx="1.5" /><path d="M8 21h8M12 17v4" /><path d="M7 13l3-3 2 2 4-4" /></>,
});

/* check dimensions → label + icon */
const FR_CAT = {
  dataset: { label: "数据集", icon: "db" },
  conn:    { label: "数据连接", icon: "link" },
  param:   { label: "参数", icon: "sliders" },
  tpl:     { label: "模板规范", icon: "grid" },
  perf:    { label: "性能", icon: "gauge" },
  perm:    { label: "权限", icon: "shield" },
};

const FR_REF_TYPES = [
  { key: "result", label: "结果表", cls: "result" },
  { key: "mid", label: "中间表", cls: "mid" },
  { key: "src", label: "源表 / 维表", cls: "src" },
  { key: "temp", label: "临时表", cls: "temp" },
];

/* tally a single report */
function reportAudit(r) {
  const issues = r.issues || [];
  const err = issues.filter(i => i.level === "err").length;
  const warn = issues.filter(i => i.level === "warn").length;
  return { err, warn, total: issues.length, level: err ? "err" : warn ? "warn" : "ok" };
}

/* type → icon + label */
function reportType(r) {
  return r.type === "frm"
    ? { icon: "screen", label: "决策报表 .frm" }
    : { icon: "grid", label: "普通报表 .cpt" };
}

/* ---- status header (报表数 / 维度 / 错误 / 警告 / 高危) ---- */
function FrStatusHeader({ d }) {
  const t = d.task;
  const s = STATUS_META[t.status] || STATUS_META.warn;
  const highRisk = d.reports.filter(r => reportAudit(r).err).length;
  return (
    <div className={"status-hero card " + s.tone}>
      <div className="sh-main">
        <div className={"sh-badge " + s.tone}><Icon name={s.icon} size={26} stroke={2.4} /></div>
        <div className="sh-text">
          <div className="sh-title-row">
            <h2 className="sh-title">{s.label}</h2>
            <Badge tone="accent" icon="grid">{t.workflow}</Badge>
          </div>
          <p className="sh-desc">{t.status === "pass" ? "全部报表通过校验，可发布" : "存在需修复的数据集 / 连接 / 权限问题"}</p>
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
        <Metric label="报表数" value={t.reports} icon="grid" />
        <Metric label="检查维度" value={t.checks} icon="layers" />
        <Metric label="错误" value={t.errors} tone={t.errors ? "err" : "ok"} icon="x" />
        <Metric label="警告" value={t.warnings} tone={t.warnings ? "warn" : "ok"} icon="alert" />
        <Metric label="高危报表" value={highRisk} tone={highRisk ? "err" : "ok"} icon="shield" />
      </div>
    </div>
  );
}

/* ---- report list ---- */
function ReportListSection({ d, reg, onOpen }) {
  const reports = d.reports || [];
  const flagged = reports.filter(r => reportAudit(r).total).length;
  const anyErr = reports.some(r => reportAudit(r).err);
  return (
    <Panel id="reports" icon="grid" title="报表检查列表" reg registerRef={reg}
      sub="数据集 · 连接 · 参数 · 模板 · 性能 · 权限"
      count={flagged ? flagged + " 张待修复" : "全部通过"} countTone={flagged ? (anyErr ? "err" : "warn") : "ok"}
      defaultOpen={true}>
      <div className="panel-body flush">
        <div className="pas-list">
          {reports.map((r, i) => {
            const a = reportAudit(r);
            const ty = reportType(r);
            return (
              <button key={i} className="fr-row" onClick={() => onOpen(r)}>
                <span className={"fr-ico " + r.type}><Icon name={ty.icon} size={16} /></span>
                <span className="pas-main">
                  <span className="fr-name">
                    <span className={"chg-tag " + r.change}>{r.change}</span>
                    {r.title}
                  </span>
                  <span className="pas-sub mono">{r.file}</span>
                </span>
                <span className="fr-meta mono">
                  <span className="fr-type">{r.type === "frm" ? "FRM" : "CPT"}</span>
                  <span className="fr-dot">·</span>
                  <span>数据集 {r.datasets.length}</span>
                  <span className="fr-dot">·</span>
                  <span>引用表 {r.refTables.length}</span>
                </span>
                <span className="pas-tags">
                  <span className="pas-grp-label">检查</span>
                  {a.total ? (
                    <>
                      {a.err ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{a.err}</span> : null}
                      {a.warn ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{a.warn}</span> : null}
                    </>
                  ) : <span className="sev ok"><Icon name="check" size={11} stroke={2.4} />通过</span>}
                </span>
                <Icon name="chevron" size={16} className="pas-chev" />
              </button>
            );
          })}
        </div>
      </div>
    </Panel>
  );
}

/* ---- reference tables roll-up ---- */
function FrRefTablesSection({ d, reg }) {
  return (
    <Panel id="reftables" icon="db" title="报表引用表汇总" reg registerRef={reg}
      count={d.refTables.length} sub="全部报表数据集去重后按类型着色">
      <div className="panel-body">
        <div className="legend" style={{ marginBottom: 14 }}>
          {FR_REF_TYPES.map(t => {
            const n = d.refTables.filter(r => r.type === t.key).length;
            if (!n) return null;
            return <span key={t.key} className="lg-item"><span className={"chip " + t.cls}><span className="cdot" />{t.label}</span><span className="mono" style={{ color: "var(--text-3)" }}>×{n}</span></span>;
          })}
        </div>
        {FR_REF_TYPES.map(t => {
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

/* ---- detail drawer ---- */
function ReportDetailDrawer({ report, onClose }) {
  const [shown, setShown] = React.useState(false);
  React.useEffect(() => {
    const r = requestAnimationFrame(() => setShown(true));
    return () => cancelAnimationFrame(r);
  }, []);
  const close = React.useCallback(() => { setShown(false); setTimeout(onClose, 220); }, [onClose]);
  React.useEffect(() => {
    const h = e => e.key === "Escape" && close();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [close]);

  const a = reportAudit(report);
  const ty = reportType(report);
  const issues = (report.issues || []).slice().sort((x, y) => (x.level === "err" ? 0 : 1) - (y.level === "err" ? 0 : 1));

  return (
    <div className={"sd-overlay" + (shown ? " shown" : "")} onClick={close}>
      <div className="sd-drawer" onClick={e => e.stopPropagation()}>
        <div className="sd-head">
          <div className="sd-head-top">
            <span className="sd-kicker"><Icon name={ty.icon} size={13} /> {ty.label}</span>
            <span className="sd-head-actions">
              <span className={"badge " + a.level}>
                <Icon name={a.level === "ok" ? "check" : a.level === "err" ? "x" : "alert"} size={11} stroke={2.4} />
                {a.level === "ok" ? "通过" : a.err ? a.err + " 错误" : a.warn + " 警告"}
              </span>
              <button className="btn ghost sm"><Icon name="download" size={13} /> 下载模板</button>
              <button className="iconbtn" style={{ width: 28, height: 28 }} onClick={close}><Icon name="x" size={15} /></button>
            </span>
          </div>
          <div className="sd-script">{report.title}</div>
          <div className="fr-path mono">{report.file}</div>
          <dl className="sd-meta">
            <div><dt>报表类型</dt><dd>{report.type === "frm" ? "决策报表（大屏）" : "普通报表"}</dd></div>
            <div><dt>数据连接</dt><dd className="mono">{report.conn}</dd></div>
            <div><dt>数据集</dt><dd className="mono">{report.datasets.length} 个 · 引用表 {report.refTables.length} 张</dd></div>
          </dl>
        </div>

        <div className="sd-body">
          {/* 审核重点 */}
          <div className="sd-focus">
            <span className="sd-focus-ic"><Icon name="search" size={14} /></span>
            <div>
              <div className="sd-focus-label">审核重点</div>
              <p className="sd-focus-text">{report.focus}</p>
            </div>
          </div>

          {/* 逐项问题表 */}
          <div className="sd-block">
            <div className="subhead">
              <Icon name="search" size={12} /> 检查问题 <span className="sd-num mono">{issues.length}</span>
              {issues.length ? (
                <span className="sd-tally">
                  {a.err ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{a.err} 错误</span> : null}
                  {a.warn ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{a.warn} 警告</span> : null}
                </span>
              ) : null}
            </div>
            {issues.length ? (
              <div className="table-wrap sd-cmp">
                <table className="tbl">
                  <thead>
                    <tr>
                      <th style={{ width: 96 }}>维度</th>
                      <th style={{ width: 110 }}>位置</th>
                      <th>规则</th>
                      <th style={{ width: 60 }}>级别</th>
                      <th>说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    {issues.map((it, i) => {
                      const c = FR_CAT[it.cat] || { label: it.cat, icon: "info" };
                      return (
                        <tr key={i} className={it.level === "err" ? "err-row" : it.level === "warn" ? "warn-row" : ""}>
                          <td><span className="fr-cat"><Icon name={c.icon} size={12} />{c.label}</span></td>
                          <td className="mono" style={{ fontSize: "var(--fs-xs)" }}>{it.loc}</td>
                          <td className="rule-cell">{it.rule}</td>
                          <td><Sev level={it.level} /></td>
                          <td>{it.msg}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : <div className="okstate"><Icon name="check" size={16} stroke={2.4} className="okic" /><span>未发现需修复的问题</span></div>}
          </div>

          {/* 数据集 */}
          <div className="sd-block">
            <div className="subhead"><Icon name="db" size={12} /> 数据集 <span className="sd-num mono">{report.datasets.length}</span></div>
            <div className="fr-ds-list">
              {report.datasets.map((ds, i) => (
                <div key={i} className="fr-ds">
                  <div className="fr-ds-top">
                    <span className="fr-ds-name mono">{ds.name}</span>
                    <span className="fr-ds-rows mono">约 {ds.rows} 行</span>
                  </div>
                  <pre className="fr-ds-sql mono">{ds.sql}</pre>
                </div>
              ))}
            </div>
          </div>

          {/* 引用表 */}
          <div className="sd-block">
            <div className="subhead"><Icon name="db" size={12} /> 引用表 <span className="sd-num mono">{report.refTables.length}</span></div>
            <div className="chips">
              {report.refTables.map((r, i) => <span key={i} className={"chip " + (r.type === "result" ? "result" : r.type === "mid" ? "mid" : "src")}><span className="cdot" />{r.name}</span>)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---- page ---- */
function FineReportResultsPage({ d, aiEnabled, reg, onJump }) {
  const [openReport, setOpenReport] = React.useState(null);
  return (
    <div className="results-page fade-in">
      <FrStatusHeader d={d} />
      <ReportListSection d={d} reg={reg} onOpen={setOpenReport} />
      <FrRefTablesSection d={d} reg={reg} />
      {aiEnabled ? <AiSection d={d} reg={reg} /> : null}
      {openReport ? <ReportDetailDrawer report={openReport} onClose={() => setOpenReport(null)} /> : null}
    </div>
  );
}

/* rail nav for FineReport workflow */
const FR_NAV = [
  { id: "overview", label: "概览", icon: "layers" },
  { id: "reports", label: "报表检查", icon: "grid", get: d => d.reports, neutral: true },
  { id: "reftables", label: "引用表汇总", icon: "db", get: d => d.refTables, neutral: true },
];

Object.assign(window, { FineReportResultsPage, ReportListSection, ReportDetailDrawer, reportAudit, FR_NAV, FR_CAT });
