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

export function syncAutoOpenScriptIds(currentIds, scripts, dismissedIds) {
  const next = new Set(currentIds);
  let changed = false;

  for (const script of Array.isArray(scripts) ? scripts : []) {
    const audit = scriptAudit(script);
    if ((audit.err || audit.warn) && !dismissedIds.has(script.script) && !next.has(script.script)) {
      next.add(script.script);
      changed = true;
    }
  }

  return changed ? next : currentIds;
}
