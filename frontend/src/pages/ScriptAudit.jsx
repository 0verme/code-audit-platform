import { Badge, Icon, OkState, Panel, Sev } from "../components/ui";
import { ReferenceTableList } from "../components/ReferenceTableList";
import {
  formatSqlReference,
  sortReferenceTableNames,
} from "../utils/resultTablePresentation";
import { scriptAudit } from "../utils/scriptAuditPresentation";
import { sortAlertRows } from "../utils/alertSorting";

const SD_STATE = {
  same: { cls: "ok", label: "相同", icon: "check" },
  missing: { cls: "err", label: "缺失", icon: "x" },
  extra: { cls: "warn", label: "多余", icon: "alert" },
};

export function getScriptLineageKey(script) {
  if (script?.lineageKey) return script.lineageKey;
  const job = String(script?.job || "").trim();
  if (job) return `job:${job.toUpperCase()}`;
  const path = String(script?.path || script?.script || "").trim().replaceAll("\\", "/").toLowerCase();
  return path ? `program:${path}` : "";
}

export function PyScriptAuditSection({ d, reg, openScriptIds, onToggle, onViewLineage, lineageEnabled }) {
  const scripts = Array.isArray(d.pyScripts) ? d.pyScripts : [];
  const flagged = scripts.filter((script) => {
    const audit = scriptAudit(script);
    return audit.err || audit.warn;
  });
  const anyErr = scripts.some((script) => scriptAudit(script).err);
  const totalCount = flagged.length;

  return (
    <Panel
      id="python"
      icon="python"
      title="Python 脚本"
      accentHeader
      registerRef={reg}
      count={totalCount || "全部通过"}
      countTone={totalCount ? (anyErr ? "err" : "warn") : "ok"}
    >
      <div className="panel-body flush">
        <div className="pas-list">
          {scripts.map((script) => {
            const audit = scriptAudit(script);
            const detailId = `script-detail-${encodeURIComponent(script.script)}`;
            const isOpen = openScriptIds.has(script.script);
            const lineageKey = getScriptLineageKey(script);
            return (
              <div key={script.script} className={`accordion-item${isOpen ? " open" : ""}`}>
                <div className="pas-row-shell">
                <button className="pas-row" onClick={() => onToggle(script.script)} aria-expanded={isOpen} aria-controls={detailId}>
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
                <button
                  type="button"
                  className="btn ghost sm pas-lineage"
                  onClick={() => onViewLineage?.({ ...script, lineageKey })}
                  disabled={!lineageEnabled || !lineageKey}
                  title={lineageEnabled ? "查看该 Python 的上下游血缘" : "审查完成后可查看"}
                ><Icon name="flow" size={13} /> 查看血缘</button>
                </div>
                <ScriptDetailAccordion script={script} detailId={detailId} open={isOpen} onClose={() => onToggle(script.script)} />
              </div>
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
      <span className="mono" style={danger ? { color: "var(--err-fg)", fontWeight: 700 } : undefined}>
        {side === "sql" ? formatSqlReference(value, row) : value}
      </span>
      {note ? <span className="cmp-note">{note}</span> : null}
    </span>
  );
}

function ListBlock({ title, items = [], icon }) {
  return (
    <div className="sd-block">
      <div className="subhead"><Icon name={icon} size={12} /> {title} <span className="sd-num mono">{items.length}</span></div>
      {items.length ? (
        <ReferenceTableList items={items} />
      ) : (
        <div className="sd-empty">无</div>
      )}
    </div>
  );
}

export function ScriptDetailAccordion({ script, detailId, open, onClose }) {
  const audit = scriptAudit(script);
  const result = Array.isArray(script?.result) ? script.result : [];
  const same = result.filter((item) => item.state === "same").length;
  const lint = sortAlertRows(script?.lint);

  return (
    <section id={detailId} className={`detail-accordion${open ? " open" : ""}`} role="region" aria-label={`${script.script} 详情`} aria-hidden={!open} inert={open ? undefined : ""}>
      <div className="detail-accordion-content">
        <div className="sd-head">
          <div className="sd-head-top">
            <span className="sd-kicker"><Icon name="python" size={13} /> 检查脚本</span>
            <span className="sd-head-actions">
              {script.downloadUrl ? (
                <a className="btn ghost sm" href={script.downloadUrl} target="_blank" rel="noreferrer"><Icon name="download" size={13} /> 下载代码</a>
              ) : (
                <button className="btn ghost sm" disabled><Icon name="download" size={13} /> 下载代码</button>
              )}
              <button className="iconbtn" style={{ width: 28, height: 28 }} onClick={onClose} aria-label="收起详情"><Icon name="x" size={15} /></button>
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
                    <tr><th>规则</th><th className="severity-cell">级别</th><th>说明</th></tr>
                  </thead>
                  <tbody>
                    {lint.map((item, index) => (
                      <tr key={index} className={item.level === "err" ? "err-row" : item.level === "warn" ? "warn-row" : ""}>
                        <td className="rule-cell">{item.rule}</td>
                        <td className="severity-cell"><Sev level={item.level} /></td>
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
              <Icon name="db" size={12} /> 结果表对比 <span className="sd-num mono">{result.length}</span>
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
                  {result.map((item, index) => {
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
          <ListBlock title="中间临时表" items={sortReferenceTableNames(script.temp)} icon="layers" />
        </div>
      </div>
    </section>
  );
}
