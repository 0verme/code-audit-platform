import { Badge, Icon, Panel, Sev } from "../ui";

export function AssetIssuesSection({ d, reg }) {
  const issues = d.assetIssues || [];
  if (!issues.length) return null;

  return (
    <Panel
      id="asset-issues"
      icon="link"
      title="资产问题"
      accentHeader
      registerRef={reg}
      count={issues.length}
      countTone="warn"
      defaultOpen
    >
      <div className="panel-body flush">
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>类型</th>
                <th>对象</th>
                <th>说明</th>
                <th>门户</th>
              </tr>
            </thead>
            <tbody>
              {issues.map((issue) => {
                const objectName =
                  issue.objectName ||
                  [issue.schemaName, issue.tableName, issue.fieldName]
                    .filter(Boolean)
                    .join(".") ||
                  issue.rootWord ||
                  "-";
                return (
                  <tr
                    key={
                      issue.issueKey ||
                      issue.hashKey ||
                      `${issue.issueType}-${objectName}`
                    }
                    className="warn-row"
                  >
                    <td>
                      <Badge tone="warn">
                        {issue.issueTitle || issue.issueType}
                      </Badge>
                    </td>
                    <td className="mono" style={{ fontSize: "var(--fs-xs)" }}>
                      {objectName}
                    </td>
                    <td>{issue.issueDesc}</td>
                    <td>
                      {issue.portalUrl ? (
                        <a
                          className="dl-link"
                          href={issue.portalUrl}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <Icon name="link" size={12} />{" "}
                          {issue.actionLabel || "打开"}
                        </a>
                      ) : (
                        <span style={{ color: "var(--text-3)" }}>未配置</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </Panel>
  );
}

export function AiSection({ d, reg }) {
  const ai = d.ai;
  if (!ai) return null;
  const tone =
    ai.verdict === "ok" ? "ok" : ai.verdict === "err" ? "err" : "warn";
  return (
    <Panel
      id="ai"
      icon="sparkle"
      title="AI 分析"
      registerRef={reg}
      sub={ai.model}
      right={
        <Badge tone={tone} icon={tone === "ok" ? "check" : "alert"}>
          {ai.verdict === "ok" ? "建议合并" : "建议修复"}
        </Badge>
      }
    >
      <div className="panel-body ai-body">
        <div className="ai-summary">
          <span className="ai-spark">
            <Icon name="sparkle" size={15} />
          </span>
          <p>{ai.summary}</p>
        </div>
        <div className="ai-findings">
          {(ai.findings || []).map((finding, index) => (
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
