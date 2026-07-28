import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  getReportElementId,
  getReportKey,
  reportAudit,
} from "../utils/fineReportPresentation.js";
import { countSqlLines } from "../utils/sqlPresentation.js";

const pageSource = [
  readFileSync(new URL("./FineReportPage.jsx", import.meta.url), "utf8"),
  readFileSync(new URL("../components/results/FineReportDatasetSqlCard.jsx", import.meta.url), "utf8"),
].join("\n");
const appSource = [
  readFileSync(new URL("../App.jsx", import.meta.url), "utf8"),
  readFileSync(new URL("../components/app/ResultRail.jsx", import.meta.url), "utf8"),
].join("\n");
const styleSource = readFileSync(new URL("../styles/fine-report.css", import.meta.url), "utf8");
const sharedStyleSource = readFileSync(new URL("../styles/styles.css", import.meta.url), "utf8");
const changeFilesSource = readFileSync(new URL("../components/results/ChangeFilesSection.jsx", import.meta.url), "utf8");
const accordionHookSource = readFileSync(new URL("../hooks/useAutoOpenAccordion.js", import.meta.url), "utf8");

test("FineReport dataset cards render summaries without inline SQL", () => {
  assert.match(pageSource, /function DatasetSqlCard\(\{ dataset, index \}\)/);
  assert.match(pageSource, /SQL \{sqlLineCount\} 行/);
  assert.match(pageSource, /结果约 \{dataset\.rows\} 行/);
  assert.match(pageSource, />\s*查看完整 SQL\s*<\/button>/);
  assert.match(pageSource, /\{viewerOpen \? \(\s*<dialog/);
  assert.doesNotMatch(pageSource, /className="fr-ds-sql"|aria-expanded=\{open\}|const \[open, setOpen\]/);
});

test("FineReport SQL viewer exposes accessible copy and close actions", () => {
  assert.match(pageSource, /className="fr-sql-viewer"/);
  assert.match(pageSource, /role="dialog"/);
  assert.match(pageSource, /aria-modal="true"/);
  assert.match(pageSource, /aria-labelledby=\{titleId\}/);
  assert.match(pageSource, /aria-describedby=\{descriptionId\}/);
  assert.match(pageSource, /aria-label=\{`复制当前数据集 \$\{datasetName\} 的完整 SQL`\}/);
  assert.match(pageSource, /aria-label="关闭 SQL 查看器"/);
  assert.match(pageSource, /role="status"\s+aria-live="polite"/);
});

test("FineReport SQL viewer copies the original SQL and reports failures", () => {
  assert.match(pageSource, /const sql = typeof dataset\?\.sql === "string" \? dataset\.sql : ""/);
  assert.match(pageSource, /await navigator\.clipboard\.writeText\(sql\)/);
  assert.match(pageSource, /setCopyFeedback\("已复制"\)/);
  assert.match(pageSource, /setCopyFeedback\("复制失败，请手动选择 SQL 复制"\)/);
  assert.match(pageSource, /useEffect\(\(\) => \(\) => clearCopyTimer\(\), \[\]\)/);
});

test("FineReport SQL viewer contains Escape and restores trigger focus", () => {
  assert.match(pageSource, /if \(event\.key !== "Escape"\) return;\s*event\.preventDefault\(\);\s*event\.stopPropagation\(\);\s*closeViewer\(\);/);
  assert.match(pageSource, /onCancel=\{\(event\) => \{\s*event\.preventDefault\(\);\s*event\.stopPropagation\(\);/);
  assert.match(pageSource, /triggerRef\.current\?\.focus\(\{ preventScroll: true \}\)/);
  assert.match(pageSource, /copyButtonRef\.current\?\.focus\(\{ preventScroll: true \}\)/);
});

test("FineReport SQL viewer keeps SQL in an independently scrolling unwrapped area", () => {
  assert.match(styleSource, /\.fr-sql-viewer-content \{[^}]*overflow-x: auto;[^}]*overflow-y: auto;[^}]*white-space: pre;/s);
  assert.match(styleSource, /\.fr-sql-viewer-toolbar \{[^}]*flex: none;/s);
  assert.match(styleSource, /\.fr-sql-viewer::backdrop \{[^}]*var\(--text\)/);
  assert.doesNotMatch(styleSource, /\.fr-sql-viewer[^}]*#[0-9a-f]{3,8}/i);
});

test("countSqlLines handles empty, LF, CRLF, and thousand-line SQL", () => {
  assert.equal(countSqlLines(null), 0);
  assert.equal(countSqlLines(undefined), 0);
  assert.equal(countSqlLines(""), 0);
  assert.equal(countSqlLines("select 1"), 1);
  assert.equal(countSqlLines("select 1\nselect 2\nselect 3"), 3);
  assert.equal(countSqlLines("select 1\r\nselect 2\r\nselect 3"), 3);
  assert.equal(countSqlLines(Array.from({ length: 1000 }, (_, index) => `select ${index}`).join("\n")), 1000);
});

test("FineReport keeps grouped referenced tables inside CPT drilldown", () => {
  assert.doesNotMatch(pageSource, /function FrRefTablesSection/);
  assert.doesNotMatch(pageSource, /id="reftables"/);
  assert.match(pageSource, /function FineReportReferenceTables\(\{ items \}\)/);
  assert.match(pageSource, /groupFineReportRefTables\(items\)/);
  assert.match(pageSource, /FINE_REPORT_REF_TABLE_GROUPS\.map/);
  assert.match(pageSource, /ReferenceTableList/);
  assert.match(pageSource, /report\.type === "cpt"/);
  assert.match(pageSource, /FineReportReferenceTables items=\{refTables\}/);
  assert.match(pageSource, /ReferenceTableList items=\{grouped\[group\.key\]\} stacked/);
});

test("FineReport details use independently expanded inline accordions", () => {
  assert.match(pageSource, /useAutoOpenAccordion\(\{/);
  assert.match(accordionHookSource, /dismissedIds\.add\(itemId\)/);
  assert.match(accordionHookSource, /dismissedIds\.delete\(itemId\)/);
  assert.match(pageSource, /<ReportListSection\s+d=\{mergedData\}\s+reg=\{reg\}\s+openReportIds=\{openReportIds\}\s+onToggle=\{toggleReport\}/);
  assert.match(pageSource, /aria-expanded=\{isOpen\}/);
  assert.match(pageSource, /ReportDetailAccordion report=\{report\} detailId=\{detailId\}/);
  assert.doesNotMatch(pageSource, /ReportDetailDrawer|sd-overlay|sd-drawer/);
});

test("FineReport report list distinguishes pending generation from an empty final result", () => {
  assert.match(pageSource, /function ReportListSection\(\{ d, reg, openReportIds, onToggle, loading = false \}\)/);
  assert.match(pageSource, /正在生成报表检查明细，请稍候/);
  assert.match(pageSource, /本次审查未发现可展示的报表检查项/);
  assert.match(pageSource, /loading=\{reportDataPending \|\| Boolean\(apiState\?\.loading\)\}/);
});

test("FineReport report navigation uses stable file targets and review status", () => {
  const report = {
    title: "风险监控日报",
    file: "fine-report/risk/RPT_RISK_MONITOR_D.cpt",
    issues: [{ level: "err" }, { level: "warn" }],
  };

  assert.equal(getReportKey(report), report.file);
  assert.equal(
    getReportElementId(report),
    "fine-report-fine-report%2Frisk%2FRPT_RISK_MONITOR_D.cpt",
  );
  assert.deepEqual(reportAudit(report), {
    err: 1,
    warn: 1,
    total: 2,
    level: "err",
  });
});

test("FineReport navigation renders every report in the expanded second-level directory", () => {
  assert.match(appSource, /new Set\(\["python", "reports"\]\)/);
  assert.match(appSource, /const fineReports = Array\.isArray\(data\?\.reports\) \? data\.reports : \[\]/);
  assert.match(appSource, /const isReports = section\.id === "reports"/);
  assert.match(appSource, /isPython \? onJumpScript\(item\) : onJumpReport\(item\)/);
  assert.match(appSource, /activeReportKey === itemKey/);
  assert.match(pageSource, /id=\{reportElementId\}/);
  assert.match(accordionHookSource, /document\.getElementById\(getElementId\(itemKey\)\)\?\.scrollIntoView/);
});

test("shared referenced table list renders FineReport table metadata", () => {
  const source = readFileSync(new URL("../components/ReferenceTableList.jsx", import.meta.url), "utf8");
  assert.match(source, /item\.disabled/);
  assert.match(source, /item\.sysNames/);
  assert.match(source, /item\.highlight \? " highlight"/);
  assert.match(source, /emptyText = "无"/);
  assert.match(source, /reference-table-list/);
  assert.match(sharedStyleSource, /\.chip\.highlight \{[^}]*var\(--err-bg\)[^}]*var\(--err-bd\)[^}]*var\(--err-fg\)/);
  assert.match(sharedStyleSource, /\.chip\.highlight \.cdot \{[^}]*var\(--err\)/);
});

test("FineReport exposes changed files plus menu and authority downloads", () => {
  assert.match(pageSource, /<ChangeFilesSection/);
  assert.match(changeFilesSource, /href=\{change\.downloadUrl\}/);
  assert.match(pageSource, /section\.downloadUrl/);
  assert.match(pageSource, /<SourceFileLinks/);
  assert.match(pageSource, /const existing = baseReports\.get\(item\.file_path\) \|\| \{\}/);
});
