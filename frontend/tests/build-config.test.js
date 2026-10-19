import assert from "node:assert/strict";
import { test } from "node:test";

import { normalizeApiBaseUrl, renderConfig } from "../scripts/build-config.js";

test("normalizeApiBaseUrl: 앞뒤 공백과 끝의 / 제거", () => {
  assert.equal(normalizeApiBaseUrl("  https://fx-api.onrender.com/ "), "https://fx-api.onrender.com");
});

test("normalizeApiBaseUrl: 비어 있으면 오류", () => {
  assert.throws(() => normalizeApiBaseUrl(""), /API_BASE_URL/);
  assert.throws(() => normalizeApiBaseUrl(undefined), /API_BASE_URL/);
});

test("normalizeApiBaseUrl: http(s)가 아니거나 URL이 아니면 오류", () => {
  assert.throws(() => normalizeApiBaseUrl("ftp://example.com"), /http/);
  assert.throws(() => normalizeApiBaseUrl("not a url"), /URL/);
});

test("renderConfig: config.js 내용 생성", () => {
  const source = renderConfig("https://fx-api.onrender.com/");
  assert.match(source, /export const API_BASE_URL = "https:\/\/fx-api\.onrender\.com";/);
});
