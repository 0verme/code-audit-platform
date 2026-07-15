import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const pageSource = readFileSync(new URL("./FineReportPage.jsx", import.meta.url), "utf8");
const styleSource = readFileSync(new URL("../styles/fine-report.css", import.meta.url), "utf8");

test("FineReport dataset SQL cards default to collapsed", () => {
  assert.match(pageSource, /function DatasetSqlCard\(\{ dataset, index \}\)/);
  assert.match(pageSource, /const \[open, setOpen\] = useState\(false\)/);
  assert.match(pageSource, /className="fr-ds-top fr-ds-trigger"/);
  assert.match(pageSource, /aria-expanded=\{open\}/);
});

test("FineReport dataset SQL cards toggle independently and render SQL only when open", () => {
  assert.match(pageSource, /onClick=\{\(\) => setOpen\(\(current\) => !current\)\}/);
  assert.match(pageSource, /\{open \? <pre id=\{sqlId\} className="fr-ds-sql mono">\{dataset\.sql\}<\/pre> : null\}/);
  assert.match(pageSource, /report\.datasets\.map\(\(dataset, index\) =>/);
  assert.match(pageSource, /key=\{`\$\{dataset\.name\}-\$\{index\}`\}/);
});

test("FineReport dataset SQL cards expose keyboard focus styling", () => {
  assert.match(styleSource, /\.fr-ds-trigger:focus-visible/);
  assert.match(styleSource, /\.fr-ds\.open \.fr-ds-chevron/);
});
