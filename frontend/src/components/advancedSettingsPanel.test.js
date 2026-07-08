import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { countEnabledAdvancedSettings } from "./advancedSettingsPanelState.js";

const panelSource = readFileSync(
  new URL("./advancedSettingsPanel.jsx", import.meta.url),
  "utf8",
);
const homePageSource = readFileSync(
  new URL("../pages/HomePage.jsx", import.meta.url),
  "utf8",
);

test("advanced settings count reflects enabled expert options", () => {
  assert.equal(countEnabledAdvancedSettings({ ai: false, dbg: false }), 0);
  assert.equal(countEnabledAdvancedSettings({ ai: true, dbg: false }), 1);
  assert.equal(countEnabledAdvancedSettings({ ai: true, dbg: true }), 2);
});

test("advanced settings panel defaults to collapsed state", () => {
  assert.match(panelSource, /useState\(defaultOpen\)/);
  assert.match(panelSource, /defaultOpen = false/);
  assert.match(panelSource, /advanced-settings-title/);
  assert.match(panelSource, /advanced-settings-subtitle/);
});

test("advanced settings toggles render only inside expanded body", () => {
  assert.match(panelSource, /open \? \(/);
  assert.match(panelSource, /advanced-settings-body/);
  assert.match(panelSource, /icon="sparkle"/);
  assert.match(panelSource, /icon="terminal"/);
});

test("advanced settings summary preserves enabled count hint", () => {
  assert.match(
    panelSource,
    /enabledCount \? \(\s*<span className="advanced-settings-count">/,
  );
  assert.match(
    panelSource,
    /onClick=\{\(\) => setOpen\(\(current\) => !current\)\}/,
  );
});

test("home page preserves original advanced option state bindings", () => {
  assert.match(homePageSource, /<AdvancedSettingsPanel/);
  assert.match(homePageSource, /ai=\{ai\}/);
  assert.match(homePageSource, /dbg=\{dbg\}/);
  assert.match(homePageSource, /onAiChange=\{setAi\}/);
  assert.match(homePageSource, /onDbgChange=\{setDbg\}/);
  assert.match(
    homePageSource,
    /buildAuditSubmitPayload\(\{\s*path,\s*ai,\s*dbg,\s*enableLocalSource: localSourceEnabled,\s*\}\)/,
  );
});
