export function formatSqlReference(value, row) {
  if (!value) return value;
  const sysNames = Array.isArray(row?.sysNames) ? row.sysNames.filter(Boolean) : [];
  const tags = [row?.disabled ? "禁用" : null, ...sysNames].filter(Boolean);
  return tags.length ? `${value}（${tags.join("/")}）` : value;
}
