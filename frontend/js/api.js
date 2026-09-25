// 백엔드 API 호출. 네트워크 오류, 타임아웃, 오류 응답을 모두 ApiError(한국어 메시지)로 바꾼다.

import { API_BASE_URL } from "./config.js";
import { errorMessage } from "./format.js";

const DEFAULT_TIMEOUT_MS = 15000;
const CHAT_TIMEOUT_MS = 70000; // GPT 응답 + Render 콜드스타트 여유

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status; // 0이면 네트워크 오류/타임아웃
  }
}

async function request(path, { method = "GET", body, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new ApiError("서버 응답이 너무 늦습니다. 잠시 후 다시 시도하세요.", 0);
    }
    throw new ApiError("서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인하세요.", 0);
  } finally {
    clearTimeout(timer);
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(errorMessage(data?.detail), response.status);
  return data;
}

const byId = (base, id) => `${base}/${encodeURIComponent(id)}`;

export const api = {
  health: (timeoutMs) => request("/health", { timeoutMs }),

  getSummary: () => request("/api/data/summary"),
  listData: () => request("/api/data"),
  createData: (item) => request("/api/data", { method: "POST", body: item }),
  updateData: (id, item) => request(byId("/api/data", id), { method: "PUT", body: item }),
  deleteData: (id) => request(byId("/api/data", id), { method: "DELETE" }),

  listConversations: () => request("/api/conversations"),
  getConversation: (id) => request(byId("/api/conversations", id)),
  deleteConversation: (id) => request(byId("/api/conversations", id), { method: "DELETE" }),

  chat: (message, conversationId) =>
    request("/api/chat", {
      method: "POST",
      body: conversationId ? { message, conversation_id: conversationId } : { message },
      timeoutMs: CHAT_TIMEOUT_MS,
    }),
};
