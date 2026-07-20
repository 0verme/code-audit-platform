import assert from "node:assert/strict";
import test from "node:test";

import { syncAutoOpenReportIds } from "./fineReportPresentation.js";

const cleanReport = { file: "clean.cpt", issues: [] };
const errorReport = { file: "error.cpt", issues: [{ level: "err" }] };
const warningReport = { file: "warning.cpt", issues: [{ level: "warn" }] };

test("FineReport findings auto-open after asynchronous results arrive", () => {
  const initiallyOpen = syncAutoOpenReportIds(new Set(), [], new Set());
  assert.deepEqual([...initiallyOpen], []);

  const autoOpened = syncAutoOpenReportIds(
    initiallyOpen,
    [cleanReport, errorReport, warningReport],
    new Set(),
  );
  assert.deepEqual([...autoOpened], ["error.cpt", "warning.cpt"]);
});

test("FineReport auto-open preserves manual dismissal and reopening", () => {
  const dismissed = new Set(["error.cpt"]);
  const manuallyOpen = new Set(["warning.cpt"]);
  const refreshed = syncAutoOpenReportIds(
    manuallyOpen,
    [cleanReport, errorReport, warningReport],
    dismissed,
  );

  assert.deepEqual([...refreshed], ["warning.cpt"]);
  assert.equal(
    syncAutoOpenReportIds(refreshed, [errorReport, warningReport], dismissed),
    refreshed,
  );

  dismissed.delete("error.cpt");
  const reopened = syncAutoOpenReportIds(refreshed, [errorReport, warningReport], dismissed);
  assert.deepEqual([...reopened], ["warning.cpt", "error.cpt"]);
});

test("FineReport auto-open ignores invalid rows and non-actionable issue levels", () => {
  const current = new Set();
  const result = syncAutoOpenReportIds(
    current,
    [null, { issues: [{ level: "err" }] }, { file: "info.cpt", issues: [{ level: "info" }] }],
    new Set(),
  );

  assert.equal(result, current);
});
