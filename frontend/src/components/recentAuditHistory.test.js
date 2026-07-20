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
const appSource = readFileSync(
  new URL("../App.jsx", import.meta.url),
  "utf8",
);
const homeStylesSource = readFileSync(
  new URL("../styles/home.css", import.meta.url),
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
  assert.match(panelSource, /recent-empty/);
});

test("home page routes recent audits through the collapsible panel", () => {
  assert.match(homePageSource, /<RecentAuditHistoryPanel/);
  assert.match(homePageSource, /loading=\{tasksState\.loading\}/);
  assert.match(homePageSource, /error=\{isApiMode \? tasksState\.error : null\}/);
  assert.match(homePageSource, /onSelect=\{handleRecentSelect\}/);
});

test("recent audit panel keeps badge display and raw source title while truncating source text", () => {
  assert.match(panelSource, /formatAuditSourceDisplay\(/);
  assert.match(panelSource, /auditSourceDisplayRules/);
  assert.match(panelSource, /className="rr-status"/);
  assert.match(panelSource, /className="rr-tag"/);
  assert.match(panelSource, /className="rr-source recent-audits-source-cell"/);
  assert.match(
    panelSource,
    /className="rr-source-text recent-audits-source-path mono"\s+title=\{sourceDisplay\.fullText\}/,
  );
  assert.match(panelSource, /\{sourceDisplay\.displayText\}/);
  assert.match(
    panelSource,
    /className="rr-wf recent-audits-type-cell"\s+title=\{workflow\.name\}/,
  );
  assert.match(panelSource, /\{workflow\.shortName\}/);
  assert.match(panelSource, /className="rr-who recent-audits-ip-cell"/);
  assert.match(panelSource, /className="rr-when recent-audits-time-cell"/);
});

test("app loads runtime source display rules with workflow configuration", () => {
  assert.match(appSource, /applyAuditSourceDisplayRules\(payload\?\.sourceDisplayRules\)/);
});

test("recent audit styles keep source flexible and type narrow", () => {
  assert.match(
    homeStylesSource,
    /\.home-wrap\s*\{[\s\S]*max-width:\s*1100px;[\s\S]*margin:\s*0 auto;[\s\S]*padding:\s*48px 16px 80px;/,
  );
  assert.match(
    homeStylesSource,
    /\.home-hero,\s*\.home-card\s*\{[\s\S]*width:\s*100%;[\s\S]*max-width:\s*708px;[\s\S]*margin-inline:\s*auto;/,
  );
  assert.match(
    homeStylesSource,
    /\.recent-head,\s*\.recent-row\s*\{[\s\S]*grid-template-columns:\s*52px minmax\(220px,\s*1fr\) 96px 104px 156px;[\s\S]*gap:\s*10px;/,
  );
  assert.match(
    homeStylesSource,
    /\.recent-table-wrap\s*\{[\s\S]*overflow-x:\s*auto;[\s\S]*min-width:\s*0;/,
  );
  assert.match(
    homeStylesSource,
    /\.recent-audits-source-cell\s*\{[\s\S]*min-width:\s*0;[\s\S]*overflow:\s*hidden;/,
  );
  assert.match(
    homeStylesSource,
    /\.recent-audits-source-path\s*\{[\s\S]*min-width:\s*0;[\s\S]*overflow:\s*hidden;[\s\S]*text-overflow:\s*ellipsis;[\s\S]*white-space:\s*nowrap;/,
  );
  assert.match(
    homeStylesSource,
    /\.recent-audits-type-cell\s*\{[\s\S]*width:\s*96px;[\s\S]*max-width:\s*96px;[\s\S]*min-width:\s*0;[\s\S]*overflow:\s*hidden;[\s\S]*text-overflow:\s*ellipsis;[\s\S]*white-space:\s*nowrap;/,
  );
  assert.match(
    homeStylesSource,
    /\.recent-audits-ip-cell\s*\{[\s\S]*width:\s*104px;[\s\S]*max-width:\s*104px;[\s\S]*white-space:\s*nowrap;/,
  );
  assert.match(
    homeStylesSource,
    /\.recent-audits-time-cell\s*\{[\s\S]*width:\s*156px;[\s\S]*max-width:\s*156px;[\s\S]*white-space:\s*nowrap;/,
  );
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
  assert.match(getRecentAuditSubtitle(20), /20/);
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
