export function scriptAudit(script) {
  const result = Array.isArray(script?.result) ? script.result : [];
  const miss = result.filter((item) => item.state === "missing").length;
  const extra = result.filter((item) => item.state === "extra").length;
  const lint = Array.isArray(script?.lint) ? script.lint : [];
  const lintErr = lint.filter((item) => item.level === "err").length;
  const lintWarn = lint.filter((item) => item.level === "warn").length;
  const err = miss + lintErr;
  const warn = extra + lintWarn;
  return { miss, extra, lintErr, lintWarn, err, warn, bad: miss + extra, level: err ? "err" : warn ? "warn" : "ok" };
}

export function getScriptKey(script) {
  return String(script?.path || script?.script || "").trim();
}

export function getScriptElementId(scriptOrKey) {
  const key = typeof scriptOrKey === "string" ? scriptOrKey : getScriptKey(scriptOrKey);
  return `python-script-${encodeURIComponent(key)}`;
}

export function syncAutoOpenScriptIds(currentIds, scripts, dismissedIds) {
  const next = new Set(currentIds);
  let changed = false;

  for (const script of Array.isArray(scripts) ? scripts : []) {
    const audit = scriptAudit(script);
    const scriptKey = getScriptKey(script);
    if (scriptKey && (audit.err || audit.warn) && !dismissedIds.has(scriptKey) && !next.has(scriptKey)) {
      next.add(scriptKey);
      changed = true;
    }
  }

  return changed ? next : currentIds;
}
