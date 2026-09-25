// 화면 표시용 순수 함수. DOM에 의존하지 않으므로 `npm test`(node --test)로 검증한다.

const TRENDS = {
  increase: { label: "증가", tone: "up" },
  decrease: { label: "감소", tone: "down" },
  flat: { label: "유지", tone: "flat" },
};

const FIELD_LABELS = {
  date: "날짜",
  value: "값",
  memo: "메모",
  message: "질문",
  conversation_id: "대화 ID",
  title: "제목",
  messages: "메시지",
  content: "내용",
  role: "역할",
};

// Pydantic 검증 오류 type → 한국어 설명. 목록에 없으면 서버가 준 원문(msg)을 쓴다.
const ERROR_TYPES = {
  greater_than: "0보다 커야 합니다",
  finite_number: "유한한 숫자여야 합니다",
  float_parsing: "숫자여야 합니다",
  float_type: "숫자여야 합니다",
  string_too_long: "너무 깁니다",
  string_too_short: "비어 있을 수 없습니다",
  too_short: "개수가 부족합니다",
  too_long: "개수가 너무 많습니다",
  missing: "필수 항목입니다",
  date_from_datetime_parsing: "날짜 형식(YYYY-MM-DD)이 올바르지 않습니다",
  date_parsing: "날짜 형식(YYYY-MM-DD)이 올바르지 않습니다",
  extra_forbidden: "허용되지 않는 항목입니다",
  string_pattern_mismatch: "형식이 올바르지 않습니다",
};

const wonFormat = new Intl.NumberFormat("ko-KR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatWon(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return `${wonFormat.format(value)}원`;
}

export function formatSignedWon(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return `${value >= 0 ? "+" : "-"}${wonFormat.format(Math.abs(value))}원`;
}

export function formatTrend(trend) {
  const known = TRENDS[trend?.direction];
  if (!known) return { label: "판단 불가", detail: "데이터가 부족합니다", tone: "none" };

  const pct = trend.change_pct;
  const sign = pct >= 0 ? "+" : "-";
  const window = trend.window;
  return {
    label: known.label,
    detail: `${sign}${Math.abs(pct).toFixed(2)}% (최근 ${window}개 vs 직전 ${window}개)`,
    tone: known.tone,
  };
}

export function errorMessage(detail) {
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail.length) {
    const parts = detail.map((error) => {
      const key = error.loc?.[error.loc.length - 1];
      const field = FIELD_LABELS[key] ?? key ?? "입력";
      return `${field} - ${ERROR_TYPES[error.type] ?? error.msg}`;
    });
    return `입력값을 확인하세요: ${parts.join(", ")}`;
  }
  return "요청을 처리하지 못했습니다.";
}

// 서버는 UTC ISO 시각을 준다. 브라우저 시간대와 관계없이 한국 시간(UTC+9)으로 표시한다.
export function formatKst(iso) {
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return "";
  const kst = new Date(time + 9 * 60 * 60 * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${kst.getUTCFullYear()}-${pad(kst.getUTCMonth() + 1)}-${pad(kst.getUTCDate())} ` +
    `${pad(kst.getUTCHours())}:${pad(kst.getUTCMinutes())}`
  );
}

export function sortByDateDesc(items) {
  return [...items].sort((a, b) => b.date.localeCompare(a.date));
}
