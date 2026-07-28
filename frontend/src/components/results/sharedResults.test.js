import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

let server;
let StatusHero;
let ChangeFilesSection;
let AssetIssuesSection;
let AiSection;

before(async () => {
  server = await createServer({
    root: fileURLToPath(new URL("../../..", import.meta.url)),
    server: { middlewareMode: true },
    appType: "custom",
    logLevel: "silent",
  });
  ({ StatusHero } = await server.ssrLoadModule(
    "/src/components/results/StatusHero.jsx",
  ));
  ({ ChangeFilesSection } = await server.ssrLoadModule(
    "/src/components/results/ChangeFilesSection.jsx",
  ));
  ({ AssetIssuesSection, AiSection } = await server.ssrLoadModule(
    "/src/components/results/SharedResultSections.jsx",
  ));
});

after(async () => {
  await server?.close();
});

const task = {
  status: "warn",
  workflow: "hcyt",
  revision: "r100",
  author: "tester",
  startedAt: "2026-07-28",
  duration: "2s",
};

test("shared status hero renders workflow state and metrics", () => {
  const markup = renderToStaticMarkup(
    StatusHero({
      data: { task },
      workflowIcon: "db",
      metrics: [{ label: "错误", value: 2, tone: "err", icon: "x" }],
    }),
  );

  assert.match(markup, /审查通过（含警告）/);
  assert.match(markup, /hcyt/);
  assert.match(markup, /错误/);
  assert.match(markup, />2</);
});

test("shared change file section preserves diff and download rendering", () => {
  const markup = renderToStaticMarkup(
    ChangeFilesSection({
      changes: [
        {
          path: "jobs/demo.sql",
          type: "M",
          cat: "DWS",
          add: 3,
          del: 1,
          downloadUrl: "/api/download/demo",
        },
      ],
      showSummary: true,
      showFileDiff: true,
    }),
  );

  assert.match(markup, /jobs\//);
  assert.match(markup, /demo\.sql/);
  assert.match(markup, /\+3/);
  assert.match(markup, /href="\/api\/download\/demo"/);
});

test("shared asset and AI sections render data and tolerate missing AI", () => {
  const assetMarkup = renderToStaticMarkup(
    AssetIssuesSection({
      d: {
        assetIssues: [
          {
            issueKey: "asset-1",
            issueTitle: "缺少登记",
            objectName: "schema.table",
            issueDesc: "资产尚未登记",
            portalUrl: "https://portal.example.test/asset-1",
          },
        ],
      },
    }),
  );
  const aiMarkup = renderToStaticMarkup(
    AiSection({
      d: {
        ai: {
          verdict: "warn",
          model: "local-model",
          summary: "建议检查",
          findings: [{ sev: "warn", title: "风险", body: "请复核" }],
        },
      },
    }),
  );

  assert.match(assetMarkup, /schema\.table/);
  assert.match(assetMarkup, /资产尚未登记/);
  assert.match(aiMarkup, /local-model/);
  assert.match(aiMarkup, /请复核/);
  assert.equal(AiSection({ d: {} }), null);
});
