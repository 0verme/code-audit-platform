const viteEnv = import.meta.env || {};

export const API_BASE_URL =
  viteEnv.VITE_API_BASE_URL?.replace(/\/$/, "") || "/api";

const rawAuditDataMode = viteEnv.VITE_AUDIT_DATA_MODE || "mock";
export const AUDIT_DATA_MODE = rawAuditDataMode === "api" ? "api" : "mock";
export const IS_API_MODE = AUDIT_DATA_MODE === "api";

export const API_PATHS = {
  health: "/health",
  projects: "/projects",
  auditTasks: "/audit-tasks",
  auditRuns: "/audit-runs",
  auditResults: "/audit-results",
  fineReportItems: "/fine-report/items",
  auditTask: (id) => `/audit-tasks/${id}`,
  auditTaskReport: (id) => `/audit-tasks/${id}/report`,
  auditRunStatus: (id) => `/audit-runs/${id}/status`,
  auditRunPartialResult: (id) => `/audit-runs/${id}/partial-result`,
};
