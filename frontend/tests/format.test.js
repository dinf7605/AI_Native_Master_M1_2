import assert from "node:assert/strict";
import { test } from "node:test";

import {
  errorMessage,
  formatKst,
  formatSignedWon,
  formatTrend,
  formatWon,
  sortByDateDesc,
} from "../js/format.js";

test("formatSignedWon: 부호를 붙인 금액", () => {
  assert.equal(formatSignedWon(-93.51), "-93.51원");
  assert.equal(formatSignedWon(1234.5), "+1,234.50원");
  assert.equal(formatSignedWon(null), "-");
});

test("formatWon: 천 단위 구분과 소수 2자리", () => {
  assert.equal(formatWon(1466.6), "1,466.60원");
  assert.equal(formatWon(1558.09), "1,558.09원");
});

test("formatWon: 값이 없으면 대시", () => {
  assert.equal(formatWon(null), "-");
  assert.equal(formatWon(undefined), "-");
});

test("formatTrend: 증가/감소/유지 라벨, 부호, 톤", () => {
  assert.deepEqual(formatTrend({ direction: "increase", change_pct: 1.94, window: 7 }), {
    label: "증가",
    detail: "+1.94% (최근 7개 vs 직전 7개)",
    tone: "up",
  });
  assert.equal(formatTrend({ direction: "decrease", change_pct: -0.8, window: 7 }).detail, "-0.80% (최근 7개 vs 직전 7개)");
  assert.equal(formatTrend({ direction: "decrease", change_pct: -0.8, window: 7 }).tone, "down");
  assert.equal(formatTrend({ direction: "flat", change_pct: 0.1, window: 7 }).label, "유지");
});

test("formatTrend: 데이터 부족", () => {
  assert.deepEqual(formatTrend({ direction: "insufficient_data", change_pct: null, window: null }), {
    label: "판단 불가",
    detail: "데이터가 부족합니다",
    tone: "none",
  });
});

test("errorMessage: 문자열 detail은 그대로", () => {
  assert.equal(errorMessage("2026-09-25 날짜의 데이터가 이미 있습니다."), "2026-09-25 날짜의 데이터가 이미 있습니다.");
});

test("errorMessage: 422 검증 오류 배열을 한국어로", () => {
  const detail = [
    { type: "greater_than", loc: ["body", "value"], msg: "Input should be greater than 0" },
    { type: "string_too_long", loc: ["body", "memo"], msg: "String should have at most 200 characters" },
  ];
  assert.equal(errorMessage(detail), "입력값을 확인하세요: 값 - 0보다 커야 합니다, 메모 - 너무 깁니다");
});

test("errorMessage: 알 수 없는 오류 유형은 원문 메시지 사용", () => {
  const detail = [{ type: "weird", loc: ["body", "date"], msg: "Something odd" }];
  assert.equal(errorMessage(detail), "입력값을 확인하세요: 날짜 - Something odd");
});

test("errorMessage: detail이 없으면 기본 문구", () => {
  assert.equal(errorMessage(undefined), "요청을 처리하지 못했습니다.");
});

test("formatKst: UTC ISO 시각을 한국 시간으로", () => {
  assert.equal(formatKst("2026-09-25T06:47:29.313915Z"), "2026-09-25 15:47");
  assert.equal(formatKst("2026-09-25T20:05:00Z"), "2026-09-26 05:05");
});

test("sortByDateDesc: 최신 날짜 먼저, 원본은 그대로", () => {
  const items = [{ date: "2026-09-23" }, { date: "2026-09-25" }, { date: "2026-09-24" }];
  const sorted = sortByDateDesc(items);
  assert.deepEqual(sorted.map((i) => i.date), ["2026-09-25", "2026-09-24", "2026-09-23"]);
  assert.equal(items[0].date, "2026-09-23");
});
