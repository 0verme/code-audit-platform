const CYCLE_MARKER = /循环依赖|成环|\bcycle\b/i;
const PATH_PATTERN = /([\w.:-]+(?:\s*(?:->|→)\s*[\w.:-]+)+)/;
const PLAN_SORTED_TABLES = new Set(["plan", "seq", "job"]);

export function getScheduleTableRows(tableKey, table) {
  const rows = Array.isArray(table?.rows) ? table.rows : [];
  const rowStates = Array.isArray(table?.rowStates) ? table.rowStates : [];
  const entries = rows.map((row, originalIndex) => ({
    row,
    state: rowStates[originalIndex],
    originalIndex,
  }));

  if (!PLAN_SORTED_TABLES.has(tableKey)) return entries;

  return entries.sort((left, right) => {
    const leftPlan = String(left.row?.[0] ?? "").trim();
    const rightPlan = String(right.row?.[0] ?? "").trim();
    if (!leftPlan && rightPlan) return 1;
    if (leftPlan && !rightPlan) return -1;
    const byPlanName = leftPlan.localeCompare(rightPlan, "zh-CN", { sensitivity: "base" });
    return byPlanName || left.originalIndex - right.originalIndex;
  });
}

export function getScheduleIssueRows(data) {
  const rows = data?.schedule?.rows;
  return Array.isArray(rows) ? rows.filter((row) => row?.level !== "ok") : [];
}

export function getScheduleIssuesByTable(data) {
  const grouped = { plan: [], seq: [], job: [] };

  for (const row of getScheduleIssueRows(data)) {
    const table = String(row?.table ?? "").trim().toUpperCase();
    const key = table === "PLAN" ? "plan" : table === "SEQ" ? "seq" : "job";
    grouped[key].push(row);
  }

  return grouped;
}

export function hasScheduleTables(data) {
  const tables = data?.schedule?.tables;
  return ["plan", "job", "seq", "cale"].some((key) => Array.isArray(tables?.[key]?.rows) && tables[key].rows.length > 0);
}

export function getCycleDependencyFindings(data) {
  const rows = getScheduleIssueRows(data);
  const findings = rows
    .filter((row) => CYCLE_MARKER.test(`${row?.rule || ""} ${row?.msg || ""}`))
    .map((row) => ({ ...row, path: getCyclePath(row) }));

  const reportedCycles = Number(data?.schedule?.summary?.cycles) || 0;
  if (!findings.length && reportedCycles > 0) {
    findings.push({
      table: "JOB",
      rule: "循环依赖检测",
      level: "err",
      msg: `检测到 ${reportedCycles} 个循环依赖，请查看调度检查明细。`,
      path: "",
    });
  }
  return findings;
}

export function getCyclePath(row) {
  const values = [row?.cyclePath, row?.cycle_path, row?.path, row?.item, row?.msg];
  for (const value of values) {
    if (typeof value !== "string") continue;
    const match = value.match(PATH_PATTERN);
    if (match) return match[1].replace(/\s*(?:->|→)\s*/g, " → ");
  }
  return "";
}

export function getPythonIssueRows(data) {
  const scripts = Array.isArray(data?.pyScripts) ? data.pyScripts : [];
  return scripts.flatMap((script) => {
    const lint = Array.isArray(script?.lint) ? script.lint : [];
    const result = Array.isArray(script?.result) ? script.result : [];
    const hasErr = lint.some((item) => item?.level === "err") || result.some((item) => item?.state === "missing");
    const hasWarn = lint.some((item) => item?.level === "warn") || result.some((item) => item?.state === "extra");
    return hasErr || hasWarn ? [{ script: script?.script, level: hasErr ? "err" : "warn" }] : [];
  });
}
