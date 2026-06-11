import { API_PATHS } from "../config/api";
import { apiClient } from "./apiClient";

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
  getAuditTask(taskId) {
    return apiClient.get(API_PATHS.auditTask(taskId));
  },
  getAuditTaskReport(taskId) {
    return apiClient.get(API_PATHS.auditTaskReport(taskId));
  },
  getAuditResults(taskId) {
    const suffix = taskId ? `?task_id=${taskId}` : "";
    return apiClient.get(`${API_PATHS.auditResults}${suffix}`);
  },
  getFineReportItems() {
    return apiClient.get(API_PATHS.fineReportItems);
  },
};
