export const LOCAL_SOURCE_DISABLED_MESSAGE =
  "当前部署模式不支持读取本地目录，请使用 SVN/Git 地址，或在本地开发模式下启用本地目录审查。";

export const UNKNOWN_SOURCE_MESSAGE =
  "审查路径未识别来源类型，请输入 svn:// 地址、Git 仓库地址，或本地目录路径。";

export const AUDIT_SOURCE_LABELS = {
  svn: "SVN",
  git: "Git",
  local_dir: "本地目录",
  unknown: "未识别",
};

function getViteEnv() {
  return import.meta.env || {};
}

export function isLocalSourceEnabled(options = {}) {
  const env = getViteEnv();
  const explicitValue = options.enableLocalSource ?? env.VITE_ENABLE_LOCAL_SOURCE;
  if (explicitValue != null && explicitValue !== "") {
    return String(explicitValue).toLowerCase() === "true";
  }
  return Boolean(options.dev ?? env.DEV);
}

function isGitHttpUrl(input) {
  if (!/^https?:\/\//i.test(input)) return false;
  return /(\.git(?:[/?#]|$)|(?:^|[/:._-])git(?:[/:._-]|$)|(?:^|[/:._-])repos?(?:[/:._-]|$))/i.test(input);
}

function isLocalDirPath(input) {
  return /^[a-zA-Z]:[\\/]/.test(input)
    || /^\/(?!\/)/.test(input)
    || /^\.\.?[\\/]/.test(input);
}

export function detectAuditSource(input, options = {}) {
  const value = String(input || "").trim();
  const localSourceEnabled = isLocalSourceEnabled(options);

  if (!value) {
    return {
      sourceType: "unknown",
      label: "?",
      valid: false,
      reason: UNKNOWN_SOURCE_MESSAGE,
    };
  }

  if (/^svn:\/\//i.test(value)) {
    return { sourceType: "svn", label: "svn", valid: true };
  }

  if (isGitHttpUrl(value)) {
    return { sourceType: "git", label: "git", valid: true };
  }

  if (isLocalDirPath(value)) {
    return {
      sourceType: "local_dir",
      label: "dir",
      valid: localSourceEnabled,
      reason: localSourceEnabled ? undefined : LOCAL_SOURCE_DISABLED_MESSAGE,
    };
  }

  return {
    sourceType: "unknown",
    label: "?",
    valid: false,
    reason: UNKNOWN_SOURCE_MESSAGE,
  };
}
