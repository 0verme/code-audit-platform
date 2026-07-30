import { Icon, OkState, Panel, ViolationTable } from "../components/ui";
import { ChangeFilesSection } from "../components/results/ChangeFilesSection";
import {
  ModuleProgressBoard,
  NUPS_MODULE_TASKS,
  ProgressiveRunPanel,
  RunLogs,
} from "../components/results/HcytRunProgress";
import { AiSection, AssetIssuesSection } from "../components/results/SharedResultSections";
import { StatusHero } from "../components/results/StatusHero";
import {
  getNupsChanges,
  getNupsPyScripts,
  getNupsSqlChecks,
  normalizeNupsMessageRows,
} from "../utils/nupsResultPresentation";

const NUPS_MESSAGE_COLUMNS = [
  { key: "rule", label: "规则", cls: "rule-cell" },
  { key: "level", label: "级别", cls: "severity-cell", width: 84, minWidth: 84 },
  { key: "msg", label: "说明" },
];

function NupsStatusHeader({ d }) {
  const task = d.task;
  return (
    <StatusHero
      data={d}
      workflowIcon="layers"
      metrics={[
        { label: "变更文件", value: task.changedFiles, icon: "file" },
        { label: "检查项", value: task.checks, icon: "layers" },
        { label: "错误", value: task.errors, tone: task.errors ? "err" : "ok", icon: "x" },
        { label: "警告", value: task.warnings, tone: task.warnings ? "warn" : "ok", icon: "alert" },
        { label: "冲突", value: task.conflicts, tone: task.conflicts ? "err" : "ok", icon: "conflict" },
      ]}
    />
  );
}

function ConflictSection({ d, reg }) {
  const conflicts = Array.isArray(d.conflicts) ? d.conflicts : [];
  const changes = getNupsChanges(d);
  if (!conflicts.length) return null;
  return (
    <Panel id="conflict" icon="conflict" title="trunk 重叠冲突文件" registerRef={reg} count={conflicts.length} countTone="err" defaultOpen>
      <div className="panel-body flush">
        <div className="flist">
          {conflicts.map((conflict) => {
            const path = typeof conflict === "string" ? conflict : conflict.path;
            const source = changes.find((change) => change.path === path)
              || (d.sourceFiles || []).find((file) => file.path === path);
            return (
              <div key={path} className="frow conflict">
                <Icon name="conflict" size={14} />
                <span className="fpath">{path}</span>
                {source?.downloadUrl ? (
                  <a className="dl-link" href={source.downloadUrl} target="_blank" rel="noreferrer">
                    <Icon name="download" size={12} /> 下载
                  </a>
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
  const rows = normalizeNupsMessageRows(messages);
  if (!rows.length) return <OkState>未发现违规项</OkState>;
  return (
    <div className="sd-cmp">
      <ViolationTable rows={rows} cols={NUPS_MESSAGE_COLUMNS} />
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

export function NupsResultsPage({ d, aiEnabled, reg, onJump }) {
  return (
    <div className="results-page fade-in">
      <ProgressiveRunPanel d={d} moduleTasks={NUPS_MODULE_TASKS} />
      <RunLogs d={d} />
      <NupsStatusHeader d={d} />
      <ModuleProgressBoard d={d} onJump={onJump} modules={NUPS_MODULE_TASKS} />
      <ChangeFilesSection changes={getNupsChanges(d)} registerRef={reg} hideWhenEmpty={false} />
      <ConflictSection d={d} reg={reg} />
      <NupsSqlSection d={d} reg={reg} />
      <NupsPySection d={d} reg={reg} />
      <AssetIssuesSection d={d} reg={reg} />
      {aiEnabled && d.ai ? <AiSection d={d} reg={reg} /> : null}
    </div>
  );
}
