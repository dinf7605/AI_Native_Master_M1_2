// 추세 그래프의 좌표 계산 (순수 함수). SVG 요소 생성은 app.js가 담당한다.
// 차트 라이브러리 없이 직접 계산해 과제의 "프레임워크 금지" 조건을 지킨다.

const DEFAULTS = {
  width: 720,
  height: 300,
  padding: { top: 16, right: 20, bottom: 32, left: 60 },
  maWindow: 7,
};

export function movingAverage(values, window) {
  const result = [];
  let sum = 0;
  values.forEach((value, i) => {
    sum += value;
    if (i >= window) sum -= values[i - window];
    result.push(i >= window - 1 ? sum / window : null);
  });
  return result;
}

function niceStep(raw) {
  const exponent = 10 ** Math.floor(Math.log10(raw));
  const fraction = raw / exponent;
  const nice = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10;
  return nice * exponent;
}

// min~max를 감싸는 1·2·5 단위 눈금
export function niceTicks(min, max, count = 5) {
  let low = min;
  let high = max;
  if (high === low) {
    const pad = Math.abs(low) * 0.01 || 1;
    low -= pad;
    high += pad;
  }
  const step = niceStep((high - low) / (count - 1));
  const start = Math.floor(low / step) * step;
  const end = Math.ceil(high / step) * step;
  const ticks = [];
  for (let value = start; value <= end + step / 2; value += step) {
    ticks.push(Number(value.toFixed(10)));
  }
  return ticks;
}

// 달이 바뀌는 첫 데이터 위치에 "N월" 라벨
export function monthTicks(dates) {
  const ticks = [];
  let previous = null;
  dates.forEach((date, index) => {
    const month = date.slice(5, 7);
    if (month !== previous) ticks.push({ index, label: `${Number(month)}월` });
    previous = month;
  });
  return ticks;
}

function toPath(coords) {
  return coords.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
}

// items는 날짜 오름차순 [{date, value}]. 2개 미만이면 null.
export function buildChartModel(items, options = {}) {
  if (items.length < 2) return null;
  const { width, height, padding, maWindow } = { ...DEFAULTS, ...options };

  const values = items.map((item) => item.value);
  const averages = movingAverage(values, maWindow);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const ticks = niceTicks(minValue, maxValue);
  const yMin = ticks[0];
  const yMax = ticks[ticks.length - 1];

  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const x = (i) => padding.left + (innerWidth * i) / (items.length - 1);
  const y = (value) => padding.top + ((yMax - value) / (yMax - yMin)) * innerHeight;

  const points = items.map((item, i) => ({
    x: x(i),
    y: y(item.value),
    date: item.date,
    value: item.value,
    average: averages[i],
  }));

  return {
    width,
    height,
    padding,
    maWindow,
    points,
    linePath: toPath(points.map((p) => [p.x, p.y])),
    maPath: toPath(points.filter((p) => p.average !== null).map((p) => [p.x, y(p.average)])),
    yTicks: ticks.map((value) => ({ value, y: y(value) })),
    xTicks: monthTicks(items.map((item) => item.date)).map((t) => ({ x: x(t.index), label: t.label })),
    minIndex: values.indexOf(minValue),
    maxIndex: values.indexOf(maxValue),
  };
}

export function nearestIndex(points, x) {
  let best = 0;
  for (let i = 1; i < points.length; i += 1) {
    if (Math.abs(points[i].x - x) < Math.abs(points[best].x - x)) best = i;
  }
  return best;
}
