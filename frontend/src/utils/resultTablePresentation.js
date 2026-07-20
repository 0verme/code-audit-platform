const TABLE_NAME_COLLATOR = new Intl.Collator("zh-CN", {
  numeric: true,
  sensitivity: "base",
});

export function formatSqlReference(value, row) {
  if (!value) return value;
  const sysNames = Array.isArray(row?.sysNames) ? row.sysNames.filter(Boolean) : [];
  const tags = [row?.disabled ? "禁用" : null, ...sysNames].filter(Boolean);
  return tags.length ? `${value}（${tags.join("/")}）` : value;
}

export function sortReferenceTableNames(items) {
  if (!Array.isArray(items)) return [];

  return items
    .map((name, originalIndex) => ({ name, originalIndex }))
    .sort((left, right) => (
      TABLE_NAME_COLLATOR.compare(String(left.name ?? ""), String(right.name ?? ""))
      || left.originalIndex - right.originalIndex
    ))
    .map(({ name }) => name);
}
