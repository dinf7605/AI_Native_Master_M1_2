// 데이터 내보내기 (CSV / JSON). 문자열 생성은 순수 함수로 두고 node 테스트로 검증한다.

const FORMULA_PREFIX = /^[=+\-@\t\r]/;

// RFC 4180 따옴표 처리. 메모는 사용자 입력이므로 엑셀이 수식으로 실행하지 않도록 '를 붙인다.
function csvCell(value, { guardFormula = false } = {}) {
  let text = String(value ?? "");
  if (guardFormula && FORMULA_PREFIX.test(text)) text = `'${text}`;
  if (/[",\r\n]/.test(text)) text = `"${text.replace(/"/g, '""')}"`;
  return text;
}

export function toCsv(items) {
  const rows = items.map(
    (item) => `${csvCell(item.date)},${csvCell(item.value)},${csvCell(item.memo, { guardFormula: true })}`,
  );
  return ["date,value,memo", ...rows].map((row) => `${row}\r\n`).join("");
}

export function toJson(items) {
  return JSON.stringify(
    items.map(({ date, value, memo }) => ({ date, value, memo })),
    null,
    2,
  );
}

export function exportFilename(extension, now = new Date()) {
  const pad = (n) => String(n).padStart(2, "0");
  const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`;
  return `usdkrw-data-${stamp}.${extension}`;
}

export function downloadText(text, filename, mimeType) {
  const url = URL.createObjectURL(new Blob([text], { type: mimeType }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
