import assert from "node:assert/strict";
import test from "node:test";
import {
  closeAccordionIds,
  openAccordionId,
  syncAutoOpenIds,
  toggleAccordionId,
} from "./useAutoOpenAccordion.js";

const getKey = (item) => String(item?.id || "");
const isActionable = (item) => item?.level === "err" || item?.level === "warn";

test("accordion sync opens new actionable items", () => {
  const current = new Set(["existing"]);
  const next = syncAutoOpenIds(
    current,
    [{ id: "clean", level: "ok" }, { id: "warning", level: "warn" }],
    new Set(),
    getKey,
    isActionable,
  );

  assert.deepEqual([...next], ["existing", "warning"]);
});

test("accordion sync preserves manual dismissals", () => {
  const current = new Set();
  const next = syncAutoOpenIds(
    current,
    [{ id: "dismissed", level: "err" }, { id: "open", level: "err" }],
    new Set(["dismissed"]),
    getKey,
    isActionable,
  );

  assert.deepEqual([...next], ["open"]);
});

test("accordion sync is stable for invalid or unchanged items", () => {
  const current = new Set(["open"]);
  const result = syncAutoOpenIds(
    current,
    [null, {}, { id: "open", level: "warn" }],
    new Set(),
    getKey,
    isActionable,
  );

  assert.equal(result, current);
  assert.equal(syncAutoOpenIds(current, null, new Set(), getKey, isActionable), current);
});

test("accordion toggle tracks manual dismissal and reopening", () => {
  const dismissed = new Set();
  const closed = toggleAccordionId(new Set(["item"]), "item", dismissed);
  assert.deepEqual([...closed], []);
  assert.deepEqual([...dismissed], ["item"]);

  const reopened = toggleAccordionId(closed, "item", dismissed);
  assert.deepEqual([...reopened], ["item"]);
  assert.deepEqual([...dismissed], []);
});

test("accordion Escape semantics close and dismiss every open item", () => {
  const dismissed = new Set(["previous"]);
  const closed = closeAccordionIds(new Set(["first", "second"]), dismissed);

  assert.deepEqual([...closed], []);
  assert.deepEqual([...dismissed], ["previous", "first", "second"]);
});

test("accordion navigation reopens a dismissed target", () => {
  const dismissed = new Set(["target"]);
  const opened = openAccordionId(new Set(), "target", dismissed);

  assert.deepEqual([...opened], ["target"]);
  assert.deepEqual([...dismissed], []);
  assert.equal(openAccordionId(opened, "target", dismissed), opened);
});
