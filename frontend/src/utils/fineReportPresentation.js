export function reportAudit(report) {
  const issues = Array.isArray(report?.issues) ? report.issues : [];
  const err = issues.filter((item) => item.level === "err").length;
  const warn = issues.filter((item) => item.level === "warn").length;
  return { err, warn, total: issues.length, level: err ? "err" : warn ? "warn" : "ok" };
}

export function getReportKey(report) {
  return String(report?.file || report?.title || "").trim();
}

export function getReportElementId(reportOrKey) {
  const key = typeof reportOrKey === "string" ? reportOrKey : getReportKey(reportOrKey);
  return `fine-report-${encodeURIComponent(key)}`;
}

export function syncAutoOpenReportIds(currentIds, reports, dismissedIds) {
  const next = new Set(currentIds);
  let changed = false;

  for (const report of Array.isArray(reports) ? reports : []) {
    const reportId = getReportKey(report);
    const issues = Array.isArray(report?.issues) ? report.issues : [];
    const hasFinding = issues.some((issue) => issue.level === "err" || issue.level === "warn");

    if (reportId && hasFinding && !dismissedIds.has(reportId) && !next.has(reportId)) {
      next.add(reportId);
      changed = true;
    }
  }

  return changed ? next : currentIds;
}

export const FINE_REPORT_REF_TABLE_GROUPS = [
  { key: "result", label: "结果表", icon: "db" },
  { key: "src", label: "码值表", icon: "grid" },
  { key: "mid", label: "中间临时表", icon: "layers" },
];

export function groupFineReportRefTables(items) {
  const grouped = {
    result: [],
    src: [],
    mid: [],
  };

  for (const rawItem of Array.isArray(items) ? items : []) {
    const item = typeof rawItem === "string" ? { name: rawItem } : rawItem;
    if (!item || typeof item !== "object") continue;

    const type = item.type === "result"
      ? "result"
      : item.type === "src"
        ? "src"
        : "mid";
    grouped[type].push({ ...item, type });
  }

  return grouped;
}
