import { shouldDefaultOpenChangeList } from "../../utils/changeListPresentation";
import { Badge, Icon, Panel } from "../ui";

export function ChangeFilesSection({
  changes = [],
  registerRef,
  title = "SVN 变更文件列表",
  hideWhenEmpty = true,
  splitPath = true,
  showSummary = false,
  showFileDiff = false,
}) {
  if (hideWhenEmpty && !changes.length) return null;

  const counts = showSummary
    ? changes.reduce((accumulator, item) => {
        accumulator[item.type] = (accumulator[item.type] || 0) + 1;
        return accumulator;
      }, {})
    : null;

  return (
    <Panel
      id="changes"
      icon="git"
      title={title}
      registerRef={registerRef}
      count={changes.length}
      countTone="info"
      defaultOpen={shouldDefaultOpenChangeList(changes.length)}
      right={
        showSummary ? (
          <span className="diffstat" style={{ marginRight: 4 }}>
            <span className="add mono">A {counts.A || 0}</span>
            <span className="del mono" style={{ color: "var(--info-fg)" }}>
              M {counts.M || 0}
            </span>
          </span>
        ) : null
      }
    >
      <div className="panel-body flush">
        <div className="flist">
          {changes.map((change) => {
            const index = splitPath ? change.path.lastIndexOf("/") + 1 : 0;
            const hasDiff =
              showFileDiff && (change.add != null || change.del != null);
            return (
              <div key={change.path} className="frow">
                <span className={`chg-tag ${change.type}`}>{change.type}</span>
                <span className="fpath">
                  {splitPath && index > 0 ? (
                    <span className="fdir">{change.path.slice(0, index)}</span>
                  ) : null}
                  {change.path.slice(index)}
                </span>
                <Badge>{change.cat}</Badge>
                {hasDiff ? (
                  <span className="diffstat">
                    <span className="add">+{change.add || 0}</span>
                    <span className="del">-{change.del || 0}</span>
                  </span>
                ) : null}
                {change.downloadUrl ? (
                  <a
                    className="dl-link"
                    href={change.downloadUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
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
