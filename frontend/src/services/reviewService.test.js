import assert from "node:assert/strict";
import test from "node:test";
import { reviewService } from "./reviewService.js";

test("startAuditRun sends the idempotency key without dropping JSON headers", async () => {
  const originalFetch = globalThis.fetch;
  let capturedOptions;
  globalThis.fetch = async (_url, options) => {
    capturedOptions = options;
    return {
      ok: true,
      status: 201,
      json: async () => ({ id: 1 }),
    };
  };

  try {
    await reviewService.startAuditRun(
      { sourceRef: "svn://example.com/hcyt" },
      { idempotencyKey: "submission-42" },
    );
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.equal(capturedOptions.headers["Content-Type"], "application/json");
  assert.equal(capturedOptions.headers["Idempotency-Key"], "submission-42");
});
