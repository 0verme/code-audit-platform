import assert from "node:assert/strict";
import test from "node:test";
import { getResultNavigation } from "./resultNavigation.js";

const ids = (workflow) => getResultNavigation(workflow).map((item) => item.id);

test("result navigation exposes every rendered section in workflow order", () => {
  assert.deepEqual(ids("hcyt"), [
    "overview", "changes", "conflict", "dws", "hive", "config", "sbin", "recv",
    "schedule", "python", "other-files", "asset-issues",
  ]);
  assert.deepEqual(ids("fine-report"), [
    "overview", "changes", "menu", "authority", "reports", "asset-issues",
  ]);
  assert.deepEqual(ids("nups"), [
    "overview", "changes", "conflict", "nups-sql", "nups-py", "asset-issues",
  ]);
});

test("unknown workflows use the HCYT navigation contract", () => {
  assert.deepEqual(ids("unknown"), ids("hcyt"));
});

test("file-backed HCYT sections remain visible when only downloads exist", () => {
  const sourceFiles = [
    { section: "dws", kind: "sql", path: "sql/demo.sql", downloadUrl: "/download/dws" },
    { section: "other-files", kind: "txt", path: "notes/readme.txt", downloadUrl: "/download/other" },
    { section: "hive", kind: "sql", path: "sql/no-download.sql" },
  ];
  const nav = getResultNavigation("hcyt");
  const report = { sourceFiles, dws: [], hive: [] };

  assert.equal(nav.find((item) => item.id === "dws").get(report).length, 1);
  assert.equal(nav.find((item) => item.id === "other-files").get(report).length, 1);
  assert.equal(nav.find((item) => item.id === "hive").get(report).length, 0);
});

test("navigation selectors safely count progressive workflow data", () => {
  const fineNav = getResultNavigation("fine-report");
  const nupsNav = getResultNavigation("nups");

  assert.equal(fineNav.find((item) => item.id === "menu").get({ menu: null }).length, 0);
  assert.equal(fineNav.find((item) => item.id === "authority").get({}).length, 0);
  assert.equal(nupsNav.find((item) => item.id === "nups-sql").get({ sqlChecks: null }).length, 0);
  assert.equal(nupsNav.find((item) => item.id === "conflict").get({ conflicts: ["demo.sql"] }).length, 1);
});
