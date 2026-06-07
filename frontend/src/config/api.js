export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:5000/api";

export const API_PATHS = {
  health: "/health",
  projects: "/projects",
  auditTasks: "/audit-tasks",
  auditResults: "/audit-results",
  fineReportItems: "/fine-report/items",
};
