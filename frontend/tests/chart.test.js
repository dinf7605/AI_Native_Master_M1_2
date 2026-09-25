import assert from "node:assert/strict";
import { test } from "node:test";

import { buildChartModel, monthTicks, movingAverage, nearestIndex, niceTicks } from "../js/chart.js";

test("movingAverage: 창 크기 이전은 null, 이후는 평균", () => {
  assert.deepEqual(movingAverage([1, 2, 3, 4], 2), [null, 1.5, 2.5, 3.5]);
});

test("movingAverage: 데이터가 창보다 적으면 모두 null", () => {
  assert.deepEqual(movingAverage([1, 2], 7), [null, null]);
});

test("niceTicks: 1·2·5 단위의 보기 좋은 눈금으로 범위를 감싼다", () => {
  assert.deepEqual(niceTicks(1336.2, 1558.09), [1300, 1400, 1500, 1600]);
  assert.deepEqual(niceTicks(100, 200), [100, 150, 200]);
});

test("niceTicks: 값이 모두 같아도 눈금을 만든다", () => {
  const ticks = niceTicks(100, 100);
  assert.ok(ticks.length >= 2);
  assert.ok(ticks[0] <= 100 && ticks[ticks.length - 1] >= 100);
});

test("monthTicks: 달이 바뀌는 첫 데이터에 월 라벨", () => {
  const dates = ["2026-03-30", "2026-03-31", "2026-04-01", "2026-04-02", "2026-05-04"];
  assert.deepEqual(monthTicks(dates), [
    { index: 0, label: "3월" },
    { index: 2, label: "4월" },
    { index: 4, label: "5월" },
  ]);
});

test("buildChartModel: 데이터가 2개 미만이면 null", () => {
  assert.equal(buildChartModel([{ date: "2026-01-01", value: 1 }]), null);
});

test("buildChartModel: 좌표와 경로, 최고·최저 인덱스", () => {
  const items = [
    { date: "2026-01-01", value: 100 },
    { date: "2026-01-02", value: 150 },
    { date: "2026-01-03", value: 200 },
  ];
  const model = buildChartModel(items, {
    width: 200,
    height: 100,
    padding: { top: 0, right: 0, bottom: 0, left: 0 },
    maWindow: 2,
  });

  assert.deepEqual(
    model.points.map((p) => [p.x, p.y]),
    [
      [0, 100],
      [100, 50],
      [200, 0],
    ],
  );
  assert.equal(model.linePath, "M0.0,100.0 L100.0,50.0 L200.0,0.0");
  assert.equal(model.maPath, "M100.0,75.0 L200.0,25.0");
  assert.deepEqual(model.yTicks.map((t) => t.value), [100, 150, 200]);
  assert.equal(model.minIndex, 0);
  assert.equal(model.maxIndex, 2);
});

test("nearestIndex: x좌표에 가장 가까운 점", () => {
  const points = [{ x: 0 }, { x: 100 }, { x: 200 }];
  assert.equal(nearestIndex(points, 40), 0);
  assert.equal(nearestIndex(points, 60), 1);
  assert.equal(nearestIndex(points, 999), 2);
});
