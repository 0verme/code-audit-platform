import { useEffect, useId, useRef, useState } from "react";
import { countSqlLines } from "../../utils/sqlPresentation";
import { Icon } from "../ui";

export function DatasetSqlCard({ dataset, index }) {
  const [viewerOpen, setViewerOpen] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState("");
  const dialogRef = useRef(null);
  const triggerRef = useRef(null);
  const copyButtonRef = useRef(null);
  const copyTimerRef = useRef(null);
  const id = useId();
  const datasetName = dataset?.name || `未命名数据集 ${index + 1}`;
  const sql = typeof dataset?.sql === "string" ? dataset.sql : "";
  const sqlLineCount = countSqlLines(sql);
  const titleId = `fr-sql-title-${id}`;
  const descriptionId = `fr-sql-description-${id}`;

  const clearCopyTimer = () => {
    if (copyTimerRef.current) {
      window.clearTimeout(copyTimerRef.current);
      copyTimerRef.current = null;
    }
  };

  useEffect(() => () => clearCopyTimer(), []);

  useEffect(() => {
    if (!viewerOpen || !dialogRef.current) return;
    if (!dialogRef.current.open) dialogRef.current.showModal();
    copyButtonRef.current?.focus({ preventScroll: true });
  }, [viewerOpen]);

  const openViewer = () => {
    clearCopyTimer();
    setCopyFeedback("");
    setViewerOpen(true);
  };

  const closeViewer = () => {
    dialogRef.current?.close();
  };

  const handleDialogClose = () => {
    clearCopyTimer();
    setCopyFeedback("");
    setViewerOpen(false);
    triggerRef.current?.focus({ preventScroll: true });
  };

  const handleDialogKeyDown = (event) => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    event.stopPropagation();
    closeViewer();
  };

  const handleCopy = async () => {
    clearCopyTimer();
    try {
      if (!navigator.clipboard?.writeText)
        throw new Error("Clipboard API unavailable");
      await navigator.clipboard.writeText(sql);
      setCopyFeedback("已复制");
      copyTimerRef.current = window.setTimeout(() => {
        setCopyFeedback("");
        copyTimerRef.current = null;
      }, 1600);
    } catch {
      setCopyFeedback("复制失败，请手动选择 SQL 复制");
    }
  };

  return (
    <>
      <div className="fr-ds">
        <div className="fr-ds-top">
          <span className="fr-ds-heading">
            <Icon name="db" size={14} />
            <span className="fr-ds-name mono">{datasetName}</span>
          </span>
          <span className="fr-ds-summary">
            <span className="fr-ds-rows mono">SQL {sqlLineCount} 行</span>
            {dataset?.rows !== null &&
            dataset?.rows !== undefined &&
            dataset?.rows !== "" ? (
              <span className="fr-ds-rows mono">结果约 {dataset.rows} 行</span>
            ) : null}
            <button
              ref={triggerRef}
              type="button"
              className="btn sm"
              onClick={openViewer}
            >
              查看完整 SQL
            </button>
          </span>
        </div>
      </div>
      {viewerOpen ? (
        <dialog
          ref={dialogRef}
          className="fr-sql-viewer"
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          aria-describedby={descriptionId}
          onClose={handleDialogClose}
          onCancel={(event) => {
            event.preventDefault();
            event.stopPropagation();
            closeViewer();
          }}
          onKeyDown={handleDialogKeyDown}
        >
          <header className="fr-sql-viewer-toolbar">
            <div className="fr-sql-viewer-heading">
              <h2 id={titleId} className="fr-sql-viewer-title">
                {datasetName}
              </h2>
              <span id={descriptionId} className="fr-sql-viewer-meta mono">
                SQL {sqlLineCount} 行
              </span>
            </div>
            <div className="fr-sql-viewer-actions">
              <span
                className="fr-sql-copy-status"
                role="status"
                aria-live="polite"
              >
                {copyFeedback}
              </span>
              <button
                ref={copyButtonRef}
                type="button"
                className="btn sm"
                onClick={handleCopy}
                title={`复制当前数据集 ${datasetName} 的完整 SQL`}
                aria-label={`复制当前数据集 ${datasetName} 的完整 SQL`}
              >
                <Icon name="copy" size={13} />
                {copyFeedback === "已复制" ? "已复制" : "复制 SQL"}
              </button>
              <button
                type="button"
                className="btn sm"
                onClick={closeViewer}
                aria-label="关闭 SQL 查看器"
              >
                <Icon name="x" size={13} />
                关闭
              </button>
            </div>
          </header>
          <pre className="fr-sql-viewer-content mono" tabIndex={0}>
            {sql}
          </pre>
        </dialog>
      ) : null}
    </>
  );
}
