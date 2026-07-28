import { useMemo } from "react";
import { ChangeFilesSection } from "../components/results/ChangeFilesSection";
import {
  FrStatusHeader,
  ReportListSection,
  TxtTableSection,
} from "../components/results/FineReportSections";
import { AiSection, AssetIssuesSection } from "../components/results/SharedResultSections";
import { useAutoOpenAccordion } from "../hooks/useAutoOpenAccordion";
import {
  getReportElementId,
  getReportKey,
  reportAudit,
} from "../utils/fineReportPresentation";

function mergeFineReportItems(baseData, items) {
  if (!items?.length) return baseData;
  const baseReports = new Map((baseData.reports || []).map((report) => [report.file, report]));
  const reports = items.map((item) => {
    const existing = baseReports.get(item.file_path) || {};
    return {
      ...existing,
      title: item.title,
      file: item.file_path,
      type: item.report_type,
      change: item.change_type,
      conn: item.connection_name,
      focus: item.focus,
      datasets: [{ name: "api_dataset", sql: item.dataset_sql || "SELECT ...", rows: item.dataset_rows || "about 1k" }],
      issues: item.issues || [],
      refTables: item.ref_tables || [],
    };
  });

  const errors = reports.flatMap((report) => report.issues).filter((issue) => issue.level === "err").length;
  const warnings = reports.flatMap((report) => report.issues).filter((issue) => issue.level === "warn").length;

  return {
    ...baseData,
    task: {
      ...baseData.task,
      reports: reports.length,
      errors,
      warnings,
      status: errors ? "fail" : warnings ? "warn" : "pass",
    },
    reports,
    refTables: reports.flatMap((report) => report.refTables),
  };
}

const hasReportFinding = (report) => Boolean(reportAudit(report).total);

export function FineReportResultsPage({ d, aiEnabled, reg, apiState, reportDataPending = false, reportJumpRequest }) {
  const mergedData = useMemo(() => mergeFineReportItems(d, apiState?.data), [d, apiState?.data]);
  const { openIds: openReportIds, toggle: toggleReport } = useAutoOpenAccordion({
    items: mergedData.reports,
    getKey: getReportKey,
    isActionable: hasReportFinding,
    jumpRequest: reportJumpRequest,
    getElementId: getReportElementId,
  });

  return (
    <div className="results-page fade-in">
      {apiState?.loading ? <div className="card" style={{ padding: 14, marginBottom: "var(--gap)" }}>正在加载报表检查数据...</div> : null}
      {apiState?.error ? <div className="card" style={{ padding: 14, marginBottom: "var(--gap)", borderColor: "var(--err)" }}>FineReport API 不可用，请检查任务接口配置。</div> : null}
      <FrStatusHeader d={mergedData} />
      <ChangeFilesSection
        changes={Array.isArray(mergedData.changes) ? mergedData.changes : []}
        registerRef={reg}
        title="变更文件列表"
        splitPath={false}
      />
      <TxtTableSection id="menu" icon="folder" title="目录检查（menu.txt）" section={mergedData.menu} reg={reg} />
      <TxtTableSection id="authority" icon="shield" title="权限检查（authority.txt）" section={mergedData.authority} reg={reg} />
      <ReportListSection
        d={mergedData}
        reg={reg}
        openReportIds={openReportIds}
        onToggle={toggleReport}
        loading={reportDataPending || Boolean(apiState?.loading)}
      />
      <AssetIssuesSection d={mergedData} reg={reg} />
      {aiEnabled ? <AiSection d={mergedData} reg={reg} /> : null}
    </div>
  );
}
