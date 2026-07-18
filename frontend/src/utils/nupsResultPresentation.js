export function normalizeNupsList(value) {
  return Array.isArray(value) ? value : [];
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
