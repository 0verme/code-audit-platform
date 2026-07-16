import assert from "node:assert/strict";
import test from "node:test";
import { createSingleFlight } from "./singleFlight.js";

test("single flight shares one active operation", async () => {
  const flight = createSingleFlight();
  let calls = 0;
  let release;
  const pending = new Promise((resolve) => {
    release = resolve;
  });

  const first = flight.run(async () => {
    calls += 1;
    await pending;
    return { id: 42 };
  });
  const second = flight.run(() => {
    calls += 1;
    return { id: 99 };
  });

  assert.equal(first, second);
  release();
  assert.deepEqual(await first, { id: 42 });
  assert.equal(calls, 1);
});

test("single flight unlocks after rejection", async () => {
  const flight = createSingleFlight();
  await assert.rejects(flight.run(() => Promise.reject(new Error("failed"))), /failed/);

  assert.equal(await flight.run(() => Promise.resolve("retried")), "retried");
});
