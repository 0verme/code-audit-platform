import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  formatRecentAuditTime,
  getRecentAuditPagination,
  getRecentAuditSubtitle,
  RECENT_AUDIT_PAGE_SIZE,
} from "./recentAuditHistory.js";

const panelSource = readFileSync(
  new URL("./RecentAuditHistoryPanel.jsx", import.meta.url),
  "utf8",
);
const homePageSource = readFileSync(
  new URL("../pages/HomePage.jsx", import.meta.url),
  "utf8",
);

function buildItems(count) {
  return Array.from({ length: count }, (_, index) => ({
    id: `task-${index + 1}`,
    rev: `r${index + 1}`,
    when: `Wed, 08 Jul 2026 21:${String(index).padStart(2, "0")}:07 GMT`,
  }));
}

test("recent audit panel defaults to collapsed and hides body until expanded", () => {
  assert.match(panelSource, /defaultOpen = false/);
  assert.match(panelSource, /const \[open, setOpen\] = useState\(defaultOpen\)/);
  assert.match(panelSource, /aria-expanded=\{open\}/);
  assert.match(panelSource, /open \? \(/);
  assert.match(panelSource, /recent-history-body/);
});

test("recent audit panel wires pagination and empty state in component source", () => {
  assert.match(panelSource, /RECENT_AUDIT_PAGE_SIZE/);
  assert.match(panelSource, /formatRecentAuditTime\(item\.when\)/);
  assert.match(panelSource, /RecentAuditPagination/);
  assert.match(panelSource, /pagination\.hasPagination \?/);
  assert.match(panelSource, /暂无最近审查记录/);
});

test("home page routes recent audits through the collapsible panel", () => {
  assert.match(homePageSource, /<RecentAuditHistoryPanel/);
  assert.match(homePageSource, /loading=\{tasksState\.loading\}/);
  assert.match(homePageSource, /error=\{isApiMode \? tasksState\.error : null\}/);
  assert.match(homePageSource, /onSelect=\{handleRecentSelect\}/);
});

test("recent audit pagination returns first page of 20 items by default", () => {
  const page = getRecentAuditPagination(buildItems(25), 1);

  assert.equal(page.pageSize, RECENT_AUDIT_PAGE_SIZE);
  assert.equal(page.currentPage, 1);
  assert.equal(page.totalItems, 25);
  assert.equal(page.totalPages, 2);
  assert.equal(page.pagedItems.length, 20);
  assert.equal(page.pagedItems[0].id, "task-1");
  assert.equal(page.pagedItems[19].id, "task-20");
});

test("recent audit pagination switches to later items on next page", () => {
  const page = getRecentAuditPagination(buildItems(25), 2);

  assert.equal(page.currentPage, 2);
  assert.equal(page.pagedItems.length, 5);
  assert.equal(page.pagedItems[0].id, "task-21");
});

test("recent audit pagination hides controls when item count does not exceed page size", () => {
  const shortPage = getRecentAuditPagination(buildItems(20), 1);

  assert.equal(shortPage.hasPagination, false);
  assert.equal(getRecentAuditSubtitle(20), "共 20 条记录");
});

test("recent audit pagination clamps page index after data refresh shrinks total pages", () => {
  const page = getRecentAuditPagination(buildItems(21), 4);

  assert.equal(page.currentPage, 2);
  assert.equal(page.totalPages, 2);
  assert.equal(page.pagedItems[0].id, "task-21");
});

test("recent audit time formatting keeps existing values and normalizes GMT timestamps", () => {
  assert.equal(
    formatRecentAuditTime("Wed, 08 Jul 2026 21:34:07 GMT"),
    "2026-07-08 21:34:07",
  );
  assert.equal(
    formatRecentAuditTime("2026-07-08 21:34:07"),
    "2026-07-08 21:34:07",
  );
  assert.equal(formatRecentAuditTime("not-a-date"), "not-a-date");
});
