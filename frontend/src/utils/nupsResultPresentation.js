export function normalizeNupsList(value) {
  return Array.isArray(value) ? value : [];
}

export function normalizeNupsMessageRows(messages) {
  return normalizeNupsList(messages).map((message) => ({
    ...message,
    rule: String(message?.rule || "").trim() || "未分类规则",
  }));
}

export function getNupsChanges(data) {
  return normalizeNupsList(data?.changes);
}

export function getNupsSqlChecks(data) {
  return normalizeNupsList(data?.sqlChecks);
}

export function getNupsPyScripts(data) {
  return normalizeNupsList(data?.pyScripts);
}
