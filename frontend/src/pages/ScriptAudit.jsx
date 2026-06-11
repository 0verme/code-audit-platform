import { useCallback, useEffect, useState } from "react";
import { Badge, Icon, OkState, Panel, Sev } from "../components/ui";

const SD_STATE = {
  same: { cls: "ok", label: "相同", icon: "check" },
  missing: { cls: "err", label: "缺失", icon: "x" },
  extra: { cls: "warn", label: "多余", icon: "alert" },
};

export function scriptAudit(script) {
  const miss = script.result.filter((item) => item.state === "missing").length;
  const extra = script.result.filter((item) => item.state === "extra").length;
  const lint = script.lint || [];
  const lintErr = lint.filter((item) => item.level === "err").length;
  const lintWarn = lint.filter((item) => item.level === "warn").length;
  const err = miss + lintErr;
  const warn = extra + lintWarn;
  return { miss, extra, lintErr, lintWarn, err, warn, bad: miss + extra, level: err ? "err" : warn ? "warn" : "ok" };
}

export function PyScriptAuditSection({ d, reg, onOpen }) {
  const scripts = d.pyScripts || [];
  const flagged = scripts.filter((script) => {
    const audit = scriptAudit(script);
    return audit.err || audit.warn;
  }).length;
  const anyErr = scripts.some((script) => scriptAudit(script).err);

  return (
    <Panel
      id="python"
      icon="python"
      title="Python 脚本检查"
      registerRef={reg}
      sub="规范检查 + SQL 引用表 / 调度依赖表一致性"
      count={flagged ? `${flagged} 项待核查` : "全部通过"}
      countTone={flagged ? (anyErr ? "err" : "warn") : "ok"}
    >
      <div className="panel-body flush">
        <div className="pas-list">
          {scripts.map((script) => {
            const audit = scriptAudit(script);
            return (
              <button key={script.script} className="pas-row" onClick={() => onOpen(script)}>
                <span className="pas-ico"><Icon name="python" size={16} /></span>
                <span className="pas-main">
                  <span className="pas-name mono">{script.script}</span>
                  <span className="pas-sub mono">{script.table} / {script.freq}</span>
                </span>
                <span className="pas-tags">
                  <span className="pas-grp">
                    <span className="pas-grp-label">检查</span>
                    {audit.lintErr ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{audit.lintErr}</span> : null}
                    {audit.lintWarn ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{audit.lintWarn}</span> : null}
                    {!audit.lintErr && !audit.lintWarn ? <span className="sev ok"><Icon name="check" size={11} stroke={2.4} /></span> : null}
                  </span>
                  <span className="pas-div" />
                  <span className="pas-grp">
                    <span className="pas-grp-label">依赖</span>
                    {audit.miss ? <span className="sev err">缺失 {audit.miss}</span> : null}
                    {audit.extra ? <span className="sev warn">多余 {audit.extra}</span> : null}
                    {!audit.miss && !audit.extra ? <span className="sev ok"><Icon name="check" size={11} stroke={2.4} />一致</span> : null}
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

function CmpCell({ value, note, side, row }) {
  if (!value) return <span className="cmp-empty">- {side === "sql" ? "脚本未引用" : "调度未配置"}</span>;
  const danger = side === "sql" && row?.highlight;
  return (
    <span className="cmp-val">
      <span className="mono" style={danger ? { color: "var(--err-fg)", fontWeight: 700 } : undefined}>{value}</span>
      {side === "sql" && row?.disabled ? <span className="cmp-note" style={{ color: "var(--err-fg)" }}>禁用</span> : null}
      {side === "sql" && row?.sysNames?.length ? <span className="cmp-note">{row.sysNames.join("/")}</span> : null}
      {note ? <span className="cmp-note">{note}</span> : null}
    </span>
  );
}

function ListBlock({ title, items, icon }) {
  return (
    <div className="sd-block">
      <div className="subhead"><Icon name={icon} size={12} /> {title} <span className="sd-num mono">{items.length}</span></div>
      {items.length ? (
        <div className="chips">
          {items.map((item) => (
            <span key={item} className="chip src"><span className="cdot" />{item}</span>
          ))}
        </div>
      ) : (
        <div className="sd-empty">无</div>
      )}
    </div>
  );
}

export function ScriptDetailDrawer({ script, onClose }) {
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const handle = requestAnimationFrame(() => setShown(true));
    return () => cancelAnimationFrame(handle);
  }, []);

  const close = useCallback(() => {
    setShown(false);
    setTimeout(onClose, 220);
  }, [onClose]);

  useEffect(() => {
    const handler = (event) => {
      if (event.key === "Escape") close();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [close]);

  const audit = scriptAudit(script);
  const same = script.result.filter((item) => item.state === "same").length;
  const lint = script.lint || [];

  return (
    <div className={`sd-overlay${shown ? " shown" : ""}`} onClick={close}>
      <div className="sd-drawer" onClick={(event) => event.stopPropagation()}>
        <div className="sd-head">
          <div className="sd-head-top">
            <span className="sd-kicker"><Icon name="python" size={13} /> 检查脚本</span>
            <span className="sd-head-actions">
              {script.downloadUrl ? (
                <a className="btn ghost sm" href={script.downloadUrl} target="_blank" rel="noreferrer"><Icon name="download" size={13} /> 下载代码</a>
              ) : (
                <button className="btn ghost sm" disabled><Icon name="download" size={13} /> 下载代码</button>
              )}
              <button className="iconbtn" style={{ width: 28, height: 28 }} onClick={close}><Icon name="x" size={15} /></button>
            </span>
          </div>
          <div className="sd-script mono">{script.script}</div>
          <dl className="sd-meta">
            <div><dt>表名</dt><dd className="mono">{script.table}</dd></div>
            <div>
              <dt>作业名</dt>
              <dd className="mono" style={script.jobDisabled ? { color: "var(--err-fg)", fontWeight: 700 } : undefined}>
                {script.job}{script.jobDisabled ? "（禁用）" : ""}
              </dd>
            </div>
            <div><dt>频率</dt><dd>{script.freq}</dd></div>
          </dl>
        </div>

        <div className="sd-body">
          <div className="sd-focus">
            <span className="sd-focus-ic"><Icon name="search" size={14} /></span>
            <div>
              <div className="sd-focus-label">审查重点</div>
              <p className="sd-focus-text">{script.focus}</p>
            </div>
          </div>

          <div className="sd-block">
            <div className="subhead">
              <Icon name="code" size={12} /> 规范检查 <span className="sd-num mono">{lint.length}</span>
              <span className="sd-tally">
                {audit.lintErr ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{audit.lintErr} 错误</span> : null}
                {audit.lintWarn ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{audit.lintWarn} 警告</span> : null}
              </span>
            </div>
            {lint.length ? (
              <div className="table-wrap sd-cmp">
                <table className="tbl">
                  <thead>
                    <tr><th className="num" style={{ width: 56 }}>行号</th><th>规则</th><th style={{ width: 64 }}>级别</th><th>说明</th></tr>
                  </thead>
                  <tbody>
                    {lint.map((item, index) => (
                      <tr key={index} className={item.level === "err" ? "err-row" : item.level === "warn" ? "warn-row" : ""}>
                        <td className="num mono">{item.line}</td>
                        <td className="rule-cell">{item.rule}</td>
                        <td><Sev level={item.level} /></td>
                        <td>{item.msg}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <OkState>未发现编码规范问题</OkState>}
          </div>

          <div className="sd-block">
            <div className="subhead">
              <Icon name="db" size={12} /> 结果表对比 <span className="sd-num mono">{script.result.length}</span>
              <span className="sd-tally">
                <span className="sev ok"><Icon name="check" size={11} stroke={2.4} />{same} 相同</span>
                {audit.miss ? <span className="sev err"><Icon name="x" size={11} stroke={2.4} />{audit.miss} 缺失</span> : null}
                {audit.extra ? <span className="sev warn"><Icon name="alert" size={11} stroke={2.4} />{audit.extra} 多余</span> : null}
              </span>
            </div>
            <div className="table-wrap sd-cmp">
              <table className="tbl">
                <thead>
                  <tr><th>SQL 引用</th><th><Icon name="flow" size={11} style={{ verticalAlign: "-1px", marginRight: 4 }} />调度依赖</th><th style={{ width: 78 }}>状态</th></tr>
                </thead>
                <tbody>
                  {script.result.map((item, index) => {
                    const meta = SD_STATE[item.state];
                    return (
                      <tr key={index} className={item.state === "missing" ? "err-row" : item.state === "extra" ? "warn-row" : ""}>
                        <td><CmpCell value={item.sql} note={item.note} side="sql" row={item} /></td>
                        <td><CmpCell value={item.dep} side="dep" /></td>
                        <td><Badge tone={meta.cls} icon={meta.icon}>{meta.label}</Badge></td>
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
