export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:5088/api";

const rawAuditDataMode = import.meta.env.VITE_AUDIT_DATA_MODE || "mock";
export const AUDIT_DATA_MODE = rawAuditDataMode === "api" ? "api" : "mock";
export const IS_API_MODE = AUDIT_DATA_MODE === "api";

export const API_PATHS = {
  health: "/health",
  projects: "/projects",
  auditTasks: "/audit-tasks",
  auditResults: "/audit-results",
  fineReportItems: "/fine-report/items",
  auditTask: (id) => `/audit-tasks/${id}`,
  auditTaskReport: (id) => `/audit-tasks/${id}/report`,
};
