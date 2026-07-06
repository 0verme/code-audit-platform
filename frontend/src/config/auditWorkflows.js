import { detectAuditSource } from "./auditSources.js";

export const UNKNOWN_WORKFLOW_MESSAGE = "当前审查路径未匹配到审查工作流，请检查路径是否包含 hcyt、fine-report、nups 等关键字。";

export const AUDIT_WORKFLOWS = [
  {
    id: "hcyt",
    key: "hcyt",
    name: "HCYT 湖仓审查",
    pathPrefix: "/hcyt",
    kw: "/hcyt/",
    desc: "DWS / Hive SQL / Python / 调度表 / 收卸配置",
    description: "DWS / Hive SQL / Python / 调度表 / 收卸配置",
    icon: "db",
    type: "hcyt",
    color: "var(--accent)",
    matchKeywords: ["/hcyt", "hcyt", "湖仓"],
  },
  {
    id: "fine-report",
    key: "fine-report",
    name: "FineReport 报表审查",
    pathPrefix: "/fine-report",
    kw: "/fine-report/",
    desc: "报表模板 / 数据集 / 参数与权限校验",
    description: "报表模板 / 数据集 / 参数与权限校验",
    icon: "grid",
    type: "fine-report",
    color: "var(--ok)",
    matchKeywords: ["/fine-report", "fine_report", "finereport", "report", "报表"],
  },
  {
    id: "nups",
    key: "nups",
    name: "NUPS 统一支付审查",
    pathPrefix: "/nups",
    kw: "/nups/",
    desc: "接口契约 / 配置文件 / 联调依赖检查",
    description: "接口契约 / 配置文件 / 联调依赖检查",
    icon: "layers",
    type: "nups",
    color: "var(--warn)",
    matchKeywords: ["/nups", "统一支付", "pay/nups", "nups"],
  },
];

export function normalizeAuditPath(path) {
  return String(path || "")
    .trim()
    .toLowerCase()
    .replaceAll("\\", "/");
}

export function detectAuditWorkflow(path) {
  const normalized = normalizeAuditPath(path);
  if (!normalized) return null;

  return AUDIT_WORKFLOWS.find((workflow) => (
    workflow.matchKeywords.some((keyword) => normalized.includes(keyword.toLowerCase()))
  )) || null;
}

export function detectWorkflow(path) {
  return detectAuditWorkflow(path)?.id || null;
}

export function canSubmitAudit(path, options = {}) {
  const source = detectAuditSource(path, options);
  return Boolean(String(path || "").trim() && source.valid && detectAuditWorkflow(path));
}

export function buildAuditSubmitPayload({ path, ai = false, dbg = false, ...options }) {
  const repoPath = String(path || "").trim();
  const source = detectAuditSource(repoPath, options);
  const workflow = detectAuditWorkflow(repoPath);
  if (!repoPath || !source.valid || !workflow) return null;

  return {
    path: repoPath,
    sourceType: source.sourceType,
    ai,
    dbg,
    workflow: workflow.id,
    type: workflow.type,
  };
}
