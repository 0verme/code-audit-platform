export const RECENT_AUDIT_PAGE_SIZE = 20;

function pad2(value) {
  return String(value).padStart(2, "0");
}

export function formatRecentAuditTime(value) {
  if (!value) return "";
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)) return value;

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  const useUtcFields = /(?:GMT|[+-]\d{2}:?\d{2}|Z)$/i.test(value);
  const year = useUtcFields ? date.getUTCFullYear() : date.getFullYear();
  const month = useUtcFields ? date.getUTCMonth() + 1 : date.getMonth() + 1;
  const day = useUtcFields ? date.getUTCDate() : date.getDate();
  const hours = useUtcFields ? date.getUTCHours() : date.getHours();
  const minutes = useUtcFields ? date.getUTCMinutes() : date.getMinutes();
  const seconds = useUtcFields ? date.getUTCSeconds() : date.getSeconds();

  return `${year}-${pad2(month)}-${pad2(day)} ${pad2(hours)}:${pad2(minutes)}:${pad2(seconds)}`;
}

export function getRecentAuditPagination(items, currentPage, pageSize = RECENT_AUDIT_PAGE_SIZE) {
  const totalItems = items.length;
  const totalPages = totalItems > 0 ? Math.ceil(totalItems / pageSize) : 1;
  const safePage = Math.min(Math.max(currentPage, 1), totalPages);
  const startIndex = (safePage - 1) * pageSize;
  const endIndex = startIndex + pageSize;

  return {
    pageSize,
    totalItems,
    totalPages,
    currentPage: safePage,
    hasPagination: totalItems > pageSize,
    pagedItems: items.slice(startIndex, endIndex),
  };
}

export function getRecentAuditSubtitle(totalItems, pageSize = RECENT_AUDIT_PAGE_SIZE) {
  if (!totalItems) return "共 0 条记录";
  if (totalItems <= pageSize) return `共 ${totalItems} 条记录`;
  return `最近 ${pageSize} 条 / 共 ${totalItems} 条`;
}
