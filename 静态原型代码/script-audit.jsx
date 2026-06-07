/* Python 脚本表依赖核对 — section list + slide-over detail drawer.
   Core: compare SQL 引用表 vs 调度依赖表; flag 缺失 / 多余 when inconsistent. */

const SD_STATE = {
  same:    { cls: "ok",   label: "相同", icon: "check" },
  missing: { cls: "err",  label: "缺失", icon: "x" },
  extra:   { cls: "warn", label: "多余", icon: "alert" },
};

/* tally lint findings + 结果表 dependency inconsistencies on a script */
function scriptAudit(s) {
  const miss = s.result.filter(r => r.state === "missing").length;
  const extra = s.result.filter(r => r.state === "extra").length;
  const lint = s.lint || [];
  const lintErr = lint.filter(l => l.level === "err").length;
  const lintWarn = lint.filter(l => l.level === "warn").length;
  const bad = miss + extra;
  const err = miss + lintErr;
  const warn = extra + lintWarn;
  return { miss, extra, bad, lintErr, lintWarn, err, warn, level: err ? "err" : warn ? "warn" : "ok" };
}

/* ---- section: clickable list of scripts ---- */
function PyScriptAuditSection({ d, reg, onOpen }) {
  const scripts = d.pyScripts || [];
  const flagged = scripts.filter(s => { const a = scriptAudit(s); return a.err || a.warn; }).length;
  const anyErr = scripts.some(s => scriptAudit(s).err);
  return (
    <Panel id="python" icon="python" title="Python 脚本检查" reg registerRef={reg}
      sub="规范检查 + SQL 引用表 / 调度依赖表一致性"
      count={flagged ? flagged + " 项待核" : "全部通过"} countTone={flagged ? (anyErr ? "err" : "warn") : "ok"}
      defaultOpen={true}>
      <div className="panel-body flush">
        <div className="pas-list">
          {scripts.map((s, i) => {
            const a = scriptAudit(s);
            return (
              <button key={i} className="pas-row" onClick={() => onOpen(s)}>
                <span className="pas-ico"><Icon name="python" size={16} /></span>
                <span className="pas-main">
                  <span className="pas-name mono">{s.script}</span>
                  <span className="pas-sub mono">{s.table} · {s.freq}</span>
                </span>
                <span className="pas-tags">
                  <span className="pas-grp">
                    <span className="pas-grp-label">检查</span>
                    {a.lintErr || a.lintWarn ? (
                      <>
                        {a.lintErr ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{a.lintErr}</span> : null}
                        {a.lintWarn ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{a.lintWarn}</span> : null}
                      </>
                    ) : <span className="sev ok"><Icon name="check" size={11} stroke={2.4} /></span>}
                  </span>
                  <span className="pas-div" />
                  <span className="pas-grp">
                    <span className="pas-grp-label">依赖</span>
                    {a.bad ? (
                      <>
                        {a.miss ? <span className="sev err">缺失 {a.miss}</span> : null}
                        {a.extra ? <span className="sev warn">多余 {a.extra}</span> : null}
                      </>
                    ) : <span className="sev ok"><Icon name="check" size={11} stroke={2.4} />一致</span>}
                  </span>
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

/* ---- comparison row in the 结果表 table ---- */
function CmpCell({ value, note, side }) {
  if (!value) return <span className="cmp-empty">— {side === "sql" ? "脚本未引用" : "调度未配置"}</span>;
  return (
    <span className="cmp-val">
      <span className="mono">{value}</span>
      {note ? <span className="cmp-note">{note}</span> : null}
    </span>
  );
}

/* ---- single-column list block (码值表 / 中间表) ---- */
function ListBlock({ title, items, icon }) {
  return (
    <div className="sd-block">
      <div className="subhead"><Icon name={icon} size={12} /> {title} <span className="sd-num mono">{items.length}</span></div>
      {items.length ? (
        <div className="chips">
          {items.map((t, i) => <span key={i} className="chip src"><span className="cdot" />{t}</span>)}
        </div>
      ) : (
        <div className="sd-empty">无</div>
      )}
    </div>
  );
}

/* ---- slide-over detail drawer ---- */
function ScriptDetailDrawer({ script, onClose }) {
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

  const a = scriptAudit(script);
  const same = script.result.filter(r => r.state === "same").length;
  const lint = script.lint || [];

  return (
    <div className={"sd-overlay" + (shown ? " shown" : "")} onClick={close}>
      <div className="sd-drawer" onClick={e => e.stopPropagation()}>
        {/* header */}
        <div className="sd-head">
          <div className="sd-head-top">
            <span className="sd-kicker"><Icon name="python" size={13} /> 检查脚本</span>
            <span className="sd-head-actions">
              <button className="btn ghost sm"><Icon name="download" size={13} /> 下载代码</button>
              <button className="iconbtn" style={{ width: 28, height: 28 }} onClick={close}><Icon name="x" size={15} /></button>
            </span>
          </div>
          <div className="sd-script mono">{script.script}</div>
          <dl className="sd-meta">
            <div><dt>表名</dt><dd className="mono">{script.table}</dd></div>
            <div><dt>作业名</dt><dd className="mono">{script.job}</dd></div>
            <div><dt>跑批频率</dt><dd>{script.freq}</dd></div>
          </dl>
        </div>

        <div className="sd-body">
          {/* 审核重点 */}
          <div className="sd-focus">
            <span className="sd-focus-ic"><Icon name="search" size={14} /></span>
            <div>
              <div className="sd-focus-label">审核重点</div>
              <p className="sd-focus-text">{script.focus}</p>
            </div>
          </div>

          {/* 规范检查 */}
          <div className="sd-block">
            <div className="subhead">
              <Icon name="code" size={12} /> 规范检查 <span className="sd-num mono">{lint.length}</span>
              {lint.length ? (
                <span className="sd-tally">
                  {a.lintErr ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{a.lintErr} 错误</span> : null}
                  {a.lintWarn ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{a.lintWarn} 警告</span> : null}
                </span>
              ) : null}
            </div>
            {lint.length ? (
              <div className="table-wrap sd-cmp">
                <table className="tbl">
                  <thead>
                    <tr><th className="num" style={{ width: 56 }}>行号</th><th>规则</th><th style={{ width: 64 }}>级别</th><th>说明</th></tr>
                  </thead>
                  <tbody>
                    {lint.map((l, i) => (
                      <tr key={i} className={l.level === "err" ? "err-row" : l.level === "warn" ? "warn-row" : ""}>
                        <td className="num mono">{l.line}</td>
                        <td className="rule-cell">{l.rule}</td>
                        <td><Sev level={l.level} /></td>
                        <td>{l.msg}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <div className="okstate"><Icon name="check" size={16} stroke={2.4} className="okic" /><span>未发现编码规范问题</span></div>}
          </div>

          {/* 结果表 comparison */}
          <div className="sd-block">
            <div className="subhead">
              <Icon name="db" size={12} /> 结果表 <span className="sd-num mono">{script.result.length}</span>
              <span className="sd-tally">
                <span className="sev ok"><Icon name="check" size={11} stroke={2.4} />{same} 相同</span>
                {a.miss ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{a.miss} 缺失</span> : null}
                {a.extra ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{a.extra} 多余</span> : null}
              </span>
            </div>
            <div className="table-wrap sd-cmp">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>SQL 引用</th>
                    <th><Icon name="flow" size={11} style={{ verticalAlign: "-1px", marginRight: 4 }} />调度依赖</th>
                    <th style={{ width: 78 }}>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {script.result.map((r, i) => {
                    const m = SD_STATE[r.state];
                    return (
                      <tr key={i} className={r.state === "missing" ? "err-row" : r.state === "extra" ? "warn-row" : ""}>
                        <td><CmpCell value={r.sql} note={r.note} side="sql" /></td>
                        <td><CmpCell value={r.dep} side="dep" /></td>
                        <td><span className={"badge " + m.cls}><Icon name={m.icon} size={11} stroke={2.4} />{m.label}</span></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <ListBlock title="码值参数表" items={script.codeval} icon="grid" />
          <ListBlock title="中间临时表" items={script.temp} icon="layers" />
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { PyScriptAuditSection, ScriptDetailDrawer, scriptAudit });
