import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("./HomePage.jsx", import.meta.url), "utf8");

test("home submit uses an immediate lock and disables the button while pending", () => {
  assert.match(source, /if \(submitLockRef\.current\) return/);
  assert.match(source, /submitLockRef\.current = true/);
  assert.match(source, /disabled=\{!canSubmit \|\| submitting \|\| submitPending\}/);
  assert.match(source, /"提交中\.\.\."/);
  assert.match(source, /finally \{/);
});
