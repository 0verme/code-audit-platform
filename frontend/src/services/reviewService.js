import { API_PATHS } from "../config/api.js";
import { apiClient } from "./apiClient.js";

export const reviewService = {
  getHealth() {
    return apiClient.get(API_PATHS.health);
  },
  getProjects() {
    return apiClient.get(API_PATHS.projects);
  },
  getAuditTasks() {
    return apiClient.get(API_PATHS.auditTasks);
  },
  createAuditTask(payload) {
    return apiClient.post(API_PATHS.auditTasks, payload);
  },
  startAuditRun(payload, { idempotencyKey } = {}) {
    return apiClient.post(API_PATHS.auditRuns, payload, {
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {},
    });
  },
  getAuditTask(taskId) {
    return apiClient.get(API_PATHS.auditTask(taskId));
  },
  getAuditTaskReport(taskId) {
    return apiClient.get(API_PATHS.auditTaskReport(taskId));
  },
  getAuditTaskLineage(taskId, params) {
    const query = new URLSearchParams(Object.entries(params).map(([key, value]) => [key, String(value)]));
    return apiClient.get(`${API_PATHS.auditTaskLineage(taskId)}?${query}`);
  },
  getAuditRunStatus(runId) {
    return apiClient.get(API_PATHS.auditRunStatus(runId));
  },
  getAuditRunPartialResult(runId) {
    return apiClient.get(API_PATHS.auditRunPartialResult(runId));
  },
  getAuditResults(taskId) {
    const suffix = taskId ? `?task_id=${taskId}` : "";
    return apiClient.get(`${API_PATHS.auditResults}${suffix}`);
  },
  getFineReportItems() {
    return apiClient.get(API_PATHS.fineReportItems);
  },
  getAuditWorkflows() {
    return apiClient.get(API_PATHS.auditWorkflows);
  },
};
