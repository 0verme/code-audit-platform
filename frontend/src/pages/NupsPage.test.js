import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const pageSource = readFileSync(new URL("./NupsPage.jsx", import.meta.url), "utf8");

test("NUPS SQL and program findings share the HCYT violation table", () => {
  assert.match(pageSource, /const NUPS_MESSAGE_COLUMNS = \[/);
  assert.match(pageSource, /\{ key: "rule", label: "规则", cls: "rule-cell" \}/);
  assert.match(pageSource, /\{ key: "level", label: "级别", cls: "severity-cell"/);
  assert.match(pageSource, /\{ key: "msg", label: "说明" \}/);
  assert.match(pageSource, /<ViolationTable rows=\{rows\} cols=\{NUPS_MESSAGE_COLUMNS\} \/>/);
  assert.equal(pageSource.match(/<MessageList messages=\{item\.messages\} \/>/g)?.length, 2);
});

test("NUPS findings keep the existing empty state and table severity styling", () => {
  assert.match(pageSource, /normalizeNupsMessageRows\(messages\)/);
  assert.match(pageSource, /<OkState>未发现违规项<\/OkState>/);
  assert.match(pageSource, /className="sd-cmp"/);
});

test("NUPS conflict files reuse task-scoped download URLs", () => {
  assert.match(pageSource, /function ConflictSection/);
  assert.match(pageSource, /changes\.find\(\(change\) => change\.path === path\)/);
  assert.match(pageSource, /<ConflictSection d=\{d\} reg=\{reg\} \/>/);
});
