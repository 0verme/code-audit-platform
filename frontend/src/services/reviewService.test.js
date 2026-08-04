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

test("audit polling bypasses browser caches", async () => {
  const originalFetch = globalThis.fetch;
  let capturedOptions;
  globalThis.fetch = async (_url, options) => {
    capturedOptions = options;
    return {
      ok: true,
      status: 200,
      json: async () => ({ runId: 42 }),
    };
  };

  try {
    await reviewService.getAuditRunPartialResult(42);
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.equal(capturedOptions.cache, "no-store");
});

test("publish-list reports an actionable error when the reverse proxy returns HTML", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 404,
    headers: { get: () => "text/html; charset=utf-8" },
    text: async () => "<html><body><h1>404 Not Found</h1></body></html>",
  });

  try {
    await assert.rejects(
      reviewService.getPublishList("2026-08-01"),
      /API 请求失败（404）.*Nginx \/api\//,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("API errors use the backend JSON message instead of stringifying the error object", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 400,
    headers: { get: () => "application/json" },
    text: async () => JSON.stringify({ error: { code: "BAD_REQUEST", message: "日期格式无效" } }),
  });

  try {
    await assert.rejects(reviewService.getPublishList("invalid"), { message: "日期格式无效" });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("publish-list export sends repeated filters and decodes the download filename", async () => {
  const originalFetch = globalThis.fetch;
  let capturedUrl;
  let capturedOptions;
  globalThis.fetch = async (url, options) => {
    capturedUrl = url;
    capturedOptions = options;
    return {
      ok: true,
      status: 200,
      headers: {
        get: (name) => name.toLowerCase() === "content-disposition"
          ? "attachment; filename=export.xlsx; filename*=UTF-8''%E4%B8%8A%E7%BA%BF%E6%B8%85%E5%8D%95_2026-08-04.xlsx"
          : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      },
      blob: async () => new Blob(["xlsx"]),
    };
  };

  try {
    const result = await reviewService.exportPublishList("2026-08-04", {
      status: "passed",
      types: ["开发维护", "数据修改"],
    });
    const url = new URL(capturedUrl, "https://example.test");
    assert.equal(url.pathname, "/api/publish-list/export");
    assert.equal(url.searchParams.get("date"), "2026-08-04");
    assert.equal(url.searchParams.get("status"), "passed");
    assert.deepEqual(url.searchParams.getAll("type"), ["开发维护", "数据修改"]);
    assert.equal(result.filename, "上线清单_2026-08-04.xlsx");
    assert.equal(result.blob.size, 4);
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.equal(capturedOptions.cache, "no-store");
});

test("publish-list export surfaces backend JSON errors", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 400,
    headers: { get: () => "application/json" },
    text: async () => JSON.stringify({ error: { message: "导出状态无效" } }),
  });

  try {
    await assert.rejects(
      reviewService.exportPublishList("2026-08-04", { status: "bogus" }),
      { message: "导出状态无效" },
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
