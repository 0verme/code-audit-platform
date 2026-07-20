export function syncAutoOpenReportIds(currentIds, reports, dismissedIds) {
  const next = new Set(currentIds);
  let changed = false;

  for (const report of Array.isArray(reports) ? reports : []) {
    const reportId = report?.file;
    const issues = Array.isArray(report?.issues) ? report.issues : [];
    const hasFinding = issues.some((issue) => issue.level === "err" || issue.level === "warn");

    if (reportId && hasFinding && !dismissedIds.has(reportId) && !next.has(reportId)) {
      next.add(reportId);
      changed = true;
    }
  }

  return changed ? next : currentIds;
}
