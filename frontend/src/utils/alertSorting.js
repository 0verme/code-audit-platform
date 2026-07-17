const LEVEL_ORDER = new Map([
  ["info", 0],
  ["warn", 1],
  ["err", 2],
  ["ok", 3],
]);

const RULE_COLLATOR = new Intl.Collator("zh-CN", {
  numeric: true,
  sensitivity: "base",
});

function levelRank(level) {
  return LEVEL_ORDER.get(String(level ?? "").trim().toLowerCase()) ?? LEVEL_ORDER.size;
}

function ruleName(row) {
  return String(row?.rule ?? "").trim();
}

export function sortAlertRows(rows) {
  if (!Array.isArray(rows)) return [];

  return rows
    .map((row, originalIndex) => ({ row, originalIndex }))
    .sort((left, right) => {
      const byLevel = levelRank(left.row?.level) - levelRank(right.row?.level);
      if (byLevel) return byLevel;

      const leftRule = ruleName(left.row);
      const rightRule = ruleName(right.row);
      if (!leftRule && rightRule) return 1;
      if (leftRule && !rightRule) return -1;

      return RULE_COLLATOR.compare(leftRule, rightRule) || left.originalIndex - right.originalIndex;
    })
    .map(({ row }) => row);
}
