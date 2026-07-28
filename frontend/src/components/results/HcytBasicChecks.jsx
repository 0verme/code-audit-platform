import { Fragment, useState } from "react";
import { Icon, levelOf, OkState, Panel, Sev, ViolationTable } from "../ui";
import { getSourceFiles, SourceFileLinks } from "../SourceFileLinks";
import { sortAlertRows } from "../../utils/alertSorting";

export function ConflictSection({ d, reg }) {
  const hasConflicts = d.conflicts.length > 0;
  if (!hasConflicts) return null;

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
            {d.conflicts.map((conflict) => {
              const source =
                d.changes.find((change) => change.path === conflict.path) ||
                (d.sourceFiles || []).find(
                  (file) => file.path === conflict.path,
                );
              return (
                <div
                  key={conflict.path}
                  className="frow conflict"
                  style={{ height: "auto", padding: "10px 12px" }}
                >
                  <Icon
                    name="conflict"
                    size={15}
                    style={{ color: "var(--err)", flex: "none" }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="fpath" style={{ color: "var(--err-fg)" }}>
                      {conflict.path}
                    </div>
                    <div
                      style={{
                        fontSize: "var(--fs-xs)",
                        color: "var(--text-2)",
                        marginTop: 3,
                      }}
                    >
                      {conflict.note}
                    </div>
                  </div>
                  <div
                    className="diffstat"
                    style={{
                      flexDirection: "column",
                      gap: 2,
                      textAlign: "right",
                    }}
                  >
                    <span className="mono" style={{ color: "var(--text-3)" }}>
                      trunk {conflict.trunkRev}
                    </span>
                    <span className="mono" style={{ color: "var(--err-fg)" }}>
                      本次 {conflict.mineRev}
                    </span>
                  </div>
                  {source?.downloadUrl ? (
                    <a
                      className="dl-link"
                      href={source.downloadUrl}
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
        ) : (
          <OkState>未检测到与 trunk 主干的重叠冲突</OkState>
        )}
      </div>
    </Panel>
  );
}

export function CheckSection({
  id,
  icon,
  title,
  rows = [],
  reg,
  okMsg,
  scriptMeta,
  sourceFiles = [],
}) {
  if (!rows.length && !scriptMeta?.script && !sourceFiles.length) return null;

  const severity = levelOf(rows);
  const errs = rows.filter((row) => row.level === "err").length;
  const warns = rows.filter((row) => row.level === "warn").length;

  return (
    <Panel
      id={id}
      icon={icon}
      title={title}
      accentHeader
      registerRef={reg}
      count={rows.length || "通过"}
      countTone={severity || "ok"}
      defaultOpen={rows.length > 0}
      right={
        rows.length ? (
          <span className="mini-counts">
            {errs ? (
              <span className="sev err">
                <Icon name="x" size={11} stroke={2.4} />
                {errs}
              </span>
            ) : null}
            {warns ? (
              <span className="sev warn">
                <Icon name="alert" size={11} stroke={2.4} />
                {warns}
              </span>
            ) : null}
          </span>
        ) : null
      }
    >
      {scriptMeta?.script ? (
        <div className="script-bar">
          <Icon name="file" size={12} /> 检查脚本：
          <span className="mono">{scriptMeta.script}</span>
          {scriptMeta.downloadUrl ? (
            <a
              className="dl-link"
              href={scriptMeta.downloadUrl}
              target="_blank"
              rel="noreferrer"
            >
              <Icon name="download" size={12} /> 下载代码
            </a>
          ) : null}
        </div>
      ) : null}
      <SourceFileLinks files={sourceFiles} />
      <div className={rows.length ? "panel-body flush" : "panel-body"}>
        {rows.length ? (
          <ViolationTable rows={rows} />
        ) : (
          <OkState>{okMsg || "未发现违规项"}</OkState>
        )}
      </div>
    </Panel>
  );
}

function ConfigFilesDetail({ files, sourceFiles, detailId }) {
  return (
    <tr className="config-detail-row">
      <td colSpan={4}>
        <section
          id={detailId}
          className="config-detail fade-in"
          role="region"
          aria-label="SCHEMA_CONFIG 详情"
        >
          {files.length ? (
            files.map((file, fileIndex) => (
              <div
                key={`${file.name}-${fileIndex}`}
                className="config-file-detail"
              >
                <div className="subhead">
                  <Icon name="file" size={12} /> {file.name}
                </div>
                {file.error ? (
                  <div className="sd-empty">{file.error}</div>
                ) : (
                  <div className="table-wrap">
                    <table className="tbl">
                      <thead>
                        <tr>
                          {file.columns.map((col) => (
                            <th key={col}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {file.rows.map((row, rowIndex) => (
                          <tr key={rowIndex}>
                            {row.map((cell, cellIndex) => (
                              <td key={cellIndex} className="mono">
                                {cell}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="sd-empty">
              已识别到 {sourceFiles.length}{" "}
              个配置文件，但暂未生成可展示的解析明细；请等待配置检查完成后重试。
            </div>
          )}
        </section>
      </td>
    </tr>
  );
}

export function ConfigCheckSection({
  rows = [],
  files = [],
  sourceFiles = [],
  reg,
}) {
  const [openRowIndex, setOpenRowIndex] = useState(null);
  if (!rows.length && !files.length && !sourceFiles.length) return null;

  const displayRows = rows.length
    ? sortAlertRows(rows)
    : [
        {
          file: "SCHEMA_CONFIG",
          rule: "",
          level: "ok",
          msg: "Schema 配置文件校验通过",
        },
      ];
  const severity = levelOf(rows);
  const errs = rows.filter((row) => row.level === "err").length;
  const warns = rows.filter((row) => row.level === "warn").length;
  const toggleRow = (rowIndex) =>
    setOpenRowIndex((current) => (current === rowIndex ? null : rowIndex));

  return (
    <Panel
      id="config"
      icon="cog"
      title="配置文件检查"
      accentHeader
      registerRef={reg}
      count={rows.length || "通过"}
      countTone={severity || "ok"}
      right={
        rows.length ? (
          <span className="mini-counts">
            {errs ? (
              <span className="sev err">
                <Icon name="x" size={11} stroke={2.4} />
                {errs}
              </span>
            ) : null}
            {warns ? (
              <span className="sev warn">
                <Icon name="alert" size={11} stroke={2.4} />
                {warns}
              </span>
            ) : null}
          </span>
        ) : null
      }
    >
      <SourceFileLinks files={sourceFiles} label="配置文件" />
      <div className="panel-body flush">
        <div className="table-wrap">
          <table className="tbl config-check-table">
            <thead>
              <tr>
                <th>文件</th>
                <th>规则</th>
                <th className="severity-cell">级别</th>
                <th>说明</th>
              </tr>
            </thead>
            <tbody>
              {displayRows.map((row, rowIndex) => {
                const isSchemaConfig =
                  String(row.file || "").toUpperCase() === "SCHEMA_CONFIG";
                const canExpand =
                  isSchemaConfig &&
                  (files.length > 0 || sourceFiles.length > 0);
                const isOpen = canExpand && openRowIndex === rowIndex;
                const detailId = `config-detail-${rowIndex}`;
                return (
                  <Fragment key={`config-item-${rowIndex}`}>
                    <tr
                      className={`${row.level === "err" ? "err-row" : row.level === "warn" ? "warn-row" : ""}${canExpand ? " config-check-row" : ""}${isOpen ? " open" : ""}`}
                      onClick={
                        canExpand ? () => toggleRow(rowIndex) : undefined
                      }
                    >
                      <td className="file-cell">
                        {canExpand ? (
                          <button
                            type="button"
                            className="config-file-trigger mono"
                            onClick={(event) => {
                              event.stopPropagation();
                              toggleRow(rowIndex);
                            }}
                            aria-expanded={isOpen}
                            aria-controls={detailId}
                          >
                            <Icon
                              name="chevron"
                              size={14}
                              className="config-row-chev"
                            />
                            {row.file}
                          </button>
                        ) : (
                          <span className="mono">{row.file}</span>
                        )}
                      </td>
                      <td className="rule-cell">{row.rule}</td>
                      <td className="severity-cell">
                        <Sev level={row.level} />
                      </td>
                      <td>{row.msg}</td>
                    </tr>
                    {isOpen ? (
                      <ConfigFilesDetail
                        files={files}
                        sourceFiles={sourceFiles}
                        detailId={detailId}
                      />
                    ) : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </Panel>
  );
}

export function OtherSourceFilesSection({ d, reg }) {
  const files = getSourceFiles(d, "other-files");
  if (!files.length) return null;
  return (
    <Panel
      id="other-files"
      icon="file"
      title="其他审计文件"
      registerRef={reg}
      count={files.length}
      countTone="info"
    >
      <SourceFileLinks files={files} label="审计输入" />
    </Panel>
  );
}
