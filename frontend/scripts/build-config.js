// 배포(Vercel) 빌드 단계에서 실행한다: 환경 변수 API_BASE_URL로 js/config.js를 생성한다.
// 정적 사이트는 브라우저에서 환경 변수를 읽을 수 없으므로, 빌드할 때 값을 파일에 넣는다.
// 사용법: API_BASE_URL=https://<백엔드>.onrender.com npm run build

import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

export function normalizeApiBaseUrl(raw) {
  const value = (raw ?? "").trim().replace(/\/+$/, "");
  if (!value) throw new Error("API_BASE_URL 환경 변수가 비어 있습니다.");

  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error(`API_BASE_URL이 올바른 URL이 아닙니다: ${value}`);
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") {
    throw new Error(`API_BASE_URL은 http(s) 주소여야 합니다: ${value}`);
  }
  return value;
}

export function renderConfig(raw) {
  return (
    "// 자동 생성 파일 (npm run build). 환경 변수 API_BASE_URL에서 만들어진다.\n" +
    `export const API_BASE_URL = ${JSON.stringify(normalizeApiBaseUrl(raw))};\n`
  );
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    const target = new URL("../js/config.js", import.meta.url);
    writeFileSync(target, renderConfig(process.env.API_BASE_URL));
    console.log(`js/config.js 생성 완료: ${normalizeApiBaseUrl(process.env.API_BASE_URL)}`);
  } catch (error) {
    console.error(`error: ${error.message}`);
    process.exit(1);
  }
}
