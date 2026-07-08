function pickPreferredSeparator(value, sourceType) {
  if (String(value || "").includes("\\")) return "\\";
  return normalizeSourceType(sourceType) === "local" ? "\\" : "/";
}

export function normalizeSourceType(sourceType) {
  const normalized = String(sourceType || "").trim().toLowerCase();
  if (normalized === "local_dir") return "local";
  if (normalized === "svn") return "svn";
  if (normalized === "git") return "git";
  if (normalized === "local") return "local";
  return "";
}

export function normalizePathForMatch(value) {
  return String(value || "").trim().replace(/\\/g, "/").toLowerCase();
}

export function findMatchedDisplayRule(rawSource, sourceType, rules = []) {
  const normalizedSourceType = normalizeSourceType(sourceType);
  const normalizedRawSource = normalizePathForMatch(rawSource);
  if (!normalizedSourceType || !normalizedRawSource) return null;

  return rules
    .filter((rule) => normalizeSourceType(rule?.sourceType) === normalizedSourceType)
    .map((rule) => ({
      ...rule,
      normalizedPrefix: normalizePathForMatch(rule?.prefix),
    }))
    .filter((rule) => rule.normalizedPrefix && normalizedRawSource.startsWith(rule.normalizedPrefix))
    .sort((left, right) => right.normalizedPrefix.length - left.normalizedPrefix.length)[0] || null;
}

export function formatAuditSourceDisplay(rawSource, sourceType, rules = []) {
  const fullText = String(rawSource || "");
  const matchedRule = findMatchedDisplayRule(fullText, sourceType, rules);

  if (!fullText) {
    return {
      displayText: "",
      fullText: "",
      matched: false,
    };
  }

  if (!matchedRule) {
    return {
      displayText: fullText,
      fullText,
      matched: false,
    };
  }

  const suffix = fullText.slice(String(matchedRule.prefix || "").length);
  const separator = pickPreferredSeparator(fullText, sourceType);
  const replacement = matchedRule.replacement ?? `…${separator}`;

  return {
    displayText: `${replacement}${suffix}`,
    fullText,
    matched: true,
  };
}
