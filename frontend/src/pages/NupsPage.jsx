import { Badge, Icon, Metric, OkState, Panel, Sev } from "../components/ui";
import { shouldDefaultOpenChangeList } from "../utils/changeListPresentation";
import { AiSection, AssetIssuesSection, STATUS_META } from "./ResultsPage";
import { sortAlertRows } from "../utils/alertSorting";
import { getNupsChanges, getNupsPyScripts, getNupsSqlChecks } from "../utils/nupsResultPresentation";

export const NUPS_NAV = [
  { id: "overview", label: "概览", icon: "layers" },
  { id: "changes", label: "变更文件", icon: "git", get: (data) => getNupsChanges(data), neutral: true },
  { id: "nups-sql", label: "NUPS SQL", icon: "db", get: (data) => getNupsSqlChecks(data), neutral: true },
  { id: "nups-py", label: "加工程序", icon: "python", get: (data) => getNupsPyScripts(data), neutral: true },
];

function NupsStatusHeader({ d }) {
  const task = d.task;
  const status = STATUS_META[task.status] || STATUS_META.warn;
  return (
    <div className={`status-hero card ${status.tone}`}>
      <div className="sh-main">
        <div className={`sh-badge ${status.tone}`}><Icon name={status.icon} size={26} stroke={2.4} /></div>
        <div className="sh-text">
          <div className="sh-title-row">
            <h2 className="sh-title">{status.label}</h2>
            <Badge tone="accent" icon="layers">{task.workflow}</Badge>
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
  const changes = getNupsChanges(d);
  return (
    <Panel
      id="changes"
      icon="git"
      title="SVN 变更文件列表"
      registerRef={reg}
      count={changes.length}
      countTone="info"
      defaultOpen={shouldDefaultOpenChangeList(changes.length)}
    >
      <div className="panel-body flush">
        <div className="flist">
          {changes.map((change) => {
            const idx = change.path.lastIndexOf("/") + 1;
            return (
              <div key={change.path} className="frow">
                <span className={`chg-tag ${change.type}`}>{change.type}</span>
                <span className="fpath"><span className="fdir">{change.path.slice(0, idx)}</span>{change.path.slice(idx)}</span>
                <Badge>{change.cat}</Badge>
                {change.downloadUrl ? (
                  <a className="dl-link" href={change.downloadUrl} target="_blank" rel="noreferrer"><Icon name="download" size={12} /> 下载</a>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    </Panel>
  );
}

function MessageList({ messages }) {
  if (!messages?.length) return <OkState>未发现违规项</OkState>;
  const sortedMessages = sortAlertRows(messages);
  return (
    <div className="fr-issue-list">
      {sortedMessages.map((msg, index) => (
        <div key={index} className={`ai-finding ${msg.level}`} style={{ marginBottom: 6 }}>
          <Sev level={msg.level} />
          <div className="aif-body"><div className="aif-text">{msg.msg}</div></div>
        </div>
      ))}
    </div>
  );
}

function NupsSqlSection({ d, reg }) {
  const items = getNupsSqlChecks(d);
  return (
    <Panel id="nups-sql" icon="db" title="NUPS SQL 检查" registerRef={reg} count={items.length || "无"} sub="cbrc / pboc / east 等系统脚本">
      <div className="panel-body">
        {items.length ? items.map((item) => (
          <div key={item.script} className="card" style={{ padding: 14, marginBottom: 12 }}>
            <div className="script-bar" style={{ border: "none", padding: "0 0 8px" }}>
              <Icon name="file" size={12} /> 检查脚本：<span className="mono">{item.script}</span>
              {item.downloadUrl ? <a className="dl-link" href={item.downloadUrl} target="_blank" rel="noreferrer"><Icon name="download" size={12} /> 下载代码</a> : null}
            </div>
            <MessageList messages={item.messages} />
          </div>
        )) : <OkState>未识别到 NUPS SQL 脚本</OkState>}
      </div>
    </Panel>
  );
}

function NupsPySection({ d, reg }) {
  const items = getNupsPyScripts(d);
  return (
    <Panel id="nups-py" icon="python" title="NUPS 加工程序检查" registerRef={reg} count={items.length || "无"} sub="规范检查 + SQL 引用表">
      <div className="panel-body">
        {items.length ? items.map((item) => (
          <div key={item.script} className="card" style={{ padding: 14, marginBottom: 12 }}>
            <div className="script-bar" style={{ border: "none", padding: "0 0 8px" }}>
              <Icon name="python" size={12} /> <span className="mono">{item.script}</span>
              {item.downloadUrl ? <a className="dl-link" href={item.downloadUrl} target="_blank" rel="noreferrer"><Icon name="download" size={12} /> 下载代码</a> : null}
            </div>
            {item.table ? <div className="mono" style={{ fontSize: "var(--fs-xs)", color: "var(--text-2)", marginBottom: 6 }}>表名：{item.table}</div> : null}
            {item.path ? <div className="mono" style={{ fontSize: "var(--fs-xs)", color: "var(--text-3)", marginBottom: 8 }}>{item.path}</div> : null}
            <MessageList messages={item.messages} />
            <div className="subhead" style={{ margin: "12px 0 7px" }}><Icon name="db" size={12} /> SQL 引用表 <span className="mono" style={{ color: "var(--text-3)" }}>{(item.sqlRefs || []).length}</span></div>
            {item.sqlRefs?.length ? (
              <div className="chips">
                {item.sqlRefs.map((name) => <span key={name} className="chip src"><span className="cdot" />{name}</span>)}
              </div>
            ) : <div className="sd-empty">无</div>}
          </div>
        )) : <OkState>未识别到 NUPS 加工程序</OkState>}
      </div>
    </Panel>
  );
}

export function NupsResultsPage({ d, aiEnabled, reg }) {
  return (
    <div className="results-page fade-in">
      <NupsStatusHeader d={d} />
      <ChangesSection d={d} reg={reg} />
      <NupsSqlSection d={d} reg={reg} />
      <NupsPySection d={d} reg={reg} />
      <AssetIssuesSection d={d} reg={reg} />
      {aiEnabled && d.ai ? <AiSection d={d} reg={reg} /> : null}
    </div>
  );
}
