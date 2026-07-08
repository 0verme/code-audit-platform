import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const homePageSource = readFileSync(new URL("../pages/HomePage.jsx", import.meta.url), "utf8");
const appSource = readFileSync(new URL("../App.jsx", import.meta.url), "utf8");
const footerBlock = appSource.slice(
  appSource.indexOf("function AppFooter"),
  appSource.indexOf("export default function App()"),
);

test("home page no longer renders runtime environment status copy", () => {
  assert.doesNotMatch(homePageSource, /当前运行环境/);
  assert.doesNotMatch(homePageSource, /审查引擎在线/);
});

test("footer keeps brand version copy without runtime badges", () => {
  assert.match(footerBlock, /APP_NAME\} \{APP_EDITION\} · \{APP_VERSION\}/);
  assert.doesNotMatch(footerBlock, /API 模式/);
  assert.doesNotMatch(footerBlock, /审查引擎在线/);
  assert.doesNotMatch(footerBlock, /LOCAL/);
  assert.doesNotMatch(footerBlock, /MOCK/);
  assert.doesNotMatch(footerBlock, /Badge/);
  assert.doesNotMatch(footerBlock, /Dot/);
});
