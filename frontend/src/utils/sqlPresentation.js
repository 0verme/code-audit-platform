export function countSqlLines(sql) {
  if (typeof sql !== "string" || sql.length === 0) return 0;
  return sql.split(/\r\n|\r|\n/).length;
}
