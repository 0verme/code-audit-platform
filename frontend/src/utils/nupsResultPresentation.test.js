import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  getNupsChanges,
  getNupsPyScripts,
  getNupsSqlChecks,
  normalizeNupsList,
} from "./nupsResultPresentation.js";

const appSource = await readFile(new URL("../App.jsx", import.meta.url), "utf8");
const pageSource = await readFile(new URL("../pages/NupsPage.jsx", import.meta.url), "utf8");

test("NUPS lists normalize missing and non-array progressive values", () => {
  assert.deepEqual(normalizeNupsList(undefined), []);
  assert.deepEqual(normalizeNupsList(null), []);
  assert.deepEqual(normalizeNupsList({}), []);
  assert.deepEqual(getNupsChanges({ changes: {} }), []);
  assert.deepEqual(getNupsSqlChecks({ sqlChecks: {} }), []);
  assert.deepEqual(getNupsPyScripts({ pyScripts: {} }), []);
});

test("NUPS list selectors preserve final report arrays", () => {
  const changes = [{ path: "NUPS_DATA/demo.sql" }];
  const sqlChecks = [{ script: "demo.sql", messages: [] }];
  const pyScripts = [{ script: "demo.py", messages: [] }];
  const report = { changes, sqlChecks, pyScripts };

  assert.equal(getNupsChanges(report), changes);
  assert.equal(getNupsSqlChecks(report), sqlChecks);
  assert.equal(getNupsPyScripts(report), pyScripts);
});

test("NUPS navigation and result sections use the safe list selectors", () => {
  assert.match(appSource, /getNupsChanges\(data\)/);
  assert.match(appSource, /getNupsSqlChecks\(data\)/);
  assert.match(appSource, /getNupsPyScripts\(data\)/);
  assert.match(pageSource, /const changes = getNupsChanges\(d\)/);
  assert.match(pageSource, /const items = getNupsSqlChecks\(d\)/);
  assert.match(pageSource, /const items = getNupsPyScripts\(d\)/);
});
