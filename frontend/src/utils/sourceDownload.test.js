import assert from "node:assert/strict";
import test from "node:test";
import { resolveSourceDownloadUrl } from "./sourceDownload.js";

test("source download URL is not prefixed with /api twice", () => {
  assert.equal(
    resolveSourceDownloadUrl("/api/audit-tasks/7/source-file?path=dws.sql"),
    "/api/audit-tasks/7/source-file?path=dws.sql",
  );
});
