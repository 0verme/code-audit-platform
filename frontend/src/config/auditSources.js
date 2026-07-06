export const LOCAL_SOURCE_DISABLED_MESSAGE =
  "当前部署模式不支持读取本地目录，请使用 SVN/Git 地址，或在本地开发模式下启用本地目录审查。";

export const UNKNOWN_SOURCE_MESSAGE =
  "审查路径未识别来源类型，请输入 svn://、svn+ssh://、Git 仓库地址或本地目录路径。";

export const AUDIT_SOURCE_LABELS = {
  local: "本地目录",
  svn: "SVN",
  git: "Git",
  selfcheck: "自检任务",
  unknown: "未识别",
};

export const AUDIT_SOURCE_TAGS = {
  local: "Local",
  svn: "SVN",
  git: "Git",
  selfcheck: "Self",
  unknown: "Unknown",
};

function getViteEnv() {
  return import.meta.env || {};
}

export function normalizeAuditSourceType(sourceType) {
  const normalized = String(sourceType || "").trim().toLowerCase();
  if (normalized === "local_dir") return "local";
  if (["local", "svn", "git", "selfcheck", "unknown"].includes(normalized)) return normalized;
  return "";
}

function isGitHttpUrl(input) {
  return /^https?:\/\//i.test(input) && (
    /\.git(?:[/?#]|$)/i.test(input)
    || /(?:^|[/:._-])git(?:[/:._-]|$)/i.test(input)
    || /(?:^|[/:._-])repos?(?:[/:._-]|$)/i.test(input)
  );
}

function isGitSshUrl(input) {
  return /^git:\/\//i.test(input)
    || /^ssh:\/\/[^/]+\/.+/i.test(input)
    || /^[^@\s]+@[^:\s]+:.+/.test(input);
}

function isSvnUrl(input) {
  return /^svn:\/\/|^svn\+ssh:\/\//i.test(input);
}

function isLocalDirPath(input) {
  return /^[a-zA-Z]:[\\/]/.test(input)
    || /^\/(?!\/)/.test(input)
    || /^\.\.?[\\/]/.test(input);
}

export function inferAuditSourceType(input) {
  const value = String(input || "").trim();
  const lower = value.toLowerCase();
  if (!value) return "unknown";
  if (lower.startsWith("local-selfcheck") || lower.includes("selfcheck") || value.includes("自检")) return "selfcheck";
  if (isSvnUrl(value)) return "svn";
  if (isGitHttpUrl(value) || isGitSshUrl(value)) return "git";
  if (isLocalDirPath(value)) return "local";
  return "unknown";
}

export function isLocalSourceEnabled(options = {}) {
  const env = getViteEnv();
  const explicitValue = options.enableLocalSource ?? env.VITE_ENABLE_LOCAL_SOURCE;
  if (explicitValue != null && explicitValue !== "") {
    return String(explicitValue).toLowerCase() === "true";
  }
  return Boolean(options.dev ?? env.DEV);
}

export function getAuditSourcePresentation(sourceType) {
  const normalized = normalizeAuditSourceType(sourceType) || "unknown";
  return {
    sourceType: normalized,
    label: AUDIT_SOURCE_LABELS[normalized],
    tag: AUDIT_SOURCE_TAGS[normalized],
  };
}

export function resolveAuditSourceMeta(record, options = {}) {
  const sourceRef = String(
    record?.source_ref
      || record?.sourceRef
      || record?.repo
      || record?.path
      || record?.repo_url
      || record?.repoUrl
      || record?.target_path
      || record?.targetPath
      || record?.workspace_path
      || record?.workspacePath
      || record?.workspace_root
      || record?.workspaceRoot
      || "",
  ).trim();
  const inferred = inferAuditSourceType(sourceRef);
  let normalized = normalizeAuditSourceType(record?.source_type || record?.sourceType) || inferred;
  if (normalized === "svn" && ["git", "local", "selfcheck"].includes(inferred)) {
    normalized = inferred;
  }
  const localSourceEnabled = isLocalSourceEnabled(options);
  const valid = normalized !== "unknown" && (normalized !== "local" || localSourceEnabled);
  const reason = normalized === "local" && !localSourceEnabled
    ? LOCAL_SOURCE_DISABLED_MESSAGE
    : (normalized === "unknown" ? UNKNOWN_SOURCE_MESSAGE : undefined);
  const presentation = getAuditSourcePresentation(normalized);

  return {
    sourceRef,
    sourceType: presentation.sourceType,
    label: presentation.label,
    tag: presentation.tag,
    valid,
    reason,
  };
}

export function detectAuditSource(input, options = {}) {
  return resolveAuditSourceMeta({ source_ref: input }, options);
}
