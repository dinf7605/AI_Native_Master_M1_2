import assert from "node:assert/strict";
import { test } from "node:test";

import { exportFilename, toCsv, toJson } from "../js/export.js";

const ITEMS = [
  { id: "a1", date: "2026-09-23", value: 1365.35, memo: "ECB reference rate (Frankfurter)" },
  { id: "a2", date: "2026-09-24", value: 1368.6, memo: "" },
];

test("toCsv: 헤더와 CRLF 줄바꿈, id는 제외", () => {
  assert.equal(
    toCsv(ITEMS),
    "date,value,memo\r\n2026-09-23,1365.35,ECB reference rate (Frankfurter)\r\n2026-09-24,1368.6,\r\n",
  );
});

test("toCsv: 쉼표·따옴표·줄바꿈이 있는 메모는 따옴표로 감싼다", () => {
  const csv = toCsv([{ date: "2026-09-24", value: 1, memo: '메모, "인용"\n둘째 줄' }]);
  assert.equal(csv.split("\r\n")[1], '2026-09-24,1,"메모, ""인용""\n둘째 줄"');
});

test("toCsv: 수식으로 해석될 수 있는 메모는 앞에 '를 붙인다 (CSV 인젝션 방지)", () => {
  for (const memo of ["=1+1", "+SUM(A1)", "-2", "@cmd"]) {
    const row = toCsv([{ date: "2026-09-24", value: 1, memo }]).split("\r\n")[1];
    assert.equal(row, `2026-09-24,1,'${memo}`);
  }
});

test("toJson: date/value/memo만 들여쓰기 JSON으로", () => {
  assert.deepEqual(JSON.parse(toJson(ITEMS)), [
    { date: "2026-09-23", value: 1365.35, memo: "ECB reference rate (Frankfurter)" },
    { date: "2026-09-24", value: 1368.6, memo: "" },
  ]);
  assert.ok(toJson(ITEMS).includes('\n  {'));
});

test("exportFilename: 날짜가 들어간 파일명", () => {
  assert.equal(exportFilename("csv", new Date(2026, 8, 5)), "usdkrw-data-20260905.csv");
});
