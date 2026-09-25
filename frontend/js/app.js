// 화면 로직. 서버·사용자·AI가 만든 텍스트는 모두 textContent로만 넣는다(innerHTML 사용 안 함).

import { api } from "./api.js";
import { buildChartModel, nearestIndex } from "./chart.js";
import { downloadText, exportFilename, toCsv, toJson } from "./export.js";
import { formatKst, formatSignedWon, formatTrend, formatWon, sortByDateDesc } from "./format.js";
import { initThemeToggle } from "./theme.js";

const WAKE_BANNER_DELAY_MS = 3000; // 이보다 오래 걸리면 "서버 깨우는 중" 안내
const WAKE_MAX_MS = 90000; // Render 무료 플랜 콜드스타트 여유
const WAKE_RETRY_MS = 3000;
const TREND_ARROWS = { up: "▲", down: "▼", flat: "▬" };

const $ = (id) => document.getElementById(id);
const emptyChat = $("chat-empty");

const state = {
  conversationId: null, // null이면 다음 질문이 새 대화를 만든다
  editingId: null,
  sending: false,
  flashDate: null,
  dataItems: [], // 날짜 오름차순. 그래프와 내보내기에 사용
};

// ---------- 공통 ----------

let toastTimer;
function showToast(message, type = "error") {
  const toast = $("toast");
  toast.textContent = message;
  toast.dataset.type = type;
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.hidden = true;
  }, 5000);
}

function createEl(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function createButton(label, className, onClick, ariaLabel) {
  const button = createEl("button", className, label);
  button.type = "button";
  if (ariaLabel) button.setAttribute("aria-label", ariaLabel);
  button.addEventListener("click", onClick);
  return button;
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// ---------- 서버 깨우기 (Render 콜드스타트 대응) ----------

function setServerStatus(stateName, text) {
  const badge = $("server-status");
  badge.dataset.state = stateName;
  badge.textContent = text;
}

async function wakeServer() {
  const bannerTimer = setTimeout(() => {
    $("wake-banner").hidden = false;
    setServerStatus("waking", "서버 깨우는 중");
  }, WAKE_BANNER_DELAY_MS);
  const deadline = Date.now() + WAKE_MAX_MS;

  try {
    for (;;) {
      try {
        await api.health(Math.max(1000, Math.min(30000, deadline - Date.now())));
        return;
      } catch (error) {
        if (Date.now() + WAKE_RETRY_MS >= deadline) throw error;
        await sleep(WAKE_RETRY_MS);
      }
    }
  } finally {
    clearTimeout(bannerTimer);
    $("wake-banner").hidden = true;
  }
}

// ---------- 요약 ----------

function setPoint(id, point) {
  $(id).textContent = formatWon(point?.value);
  $(`${id}-date`).textContent = point?.date ?? "";
}

function renderSummary(summary) {
  $("sum-period").textContent = summary.count
    ? `${summary.start_date} ~ ${summary.end_date}`
    : "데이터 없음";
  $("sum-count").textContent = `${summary.count}개`;
  $("sum-mean").textContent = formatWon(summary.mean);
  setPoint("sum-min", summary.min);
  setPoint("sum-max", summary.max);
  setPoint("sum-latest", summary.latest);

  const trend = formatTrend(summary.trend);
  const trendEl = $("sum-trend");
  trendEl.textContent = `${TREND_ARROWS[trend.tone] ?? ""} ${trend.label}`.trim();
  trendEl.dataset.tone = trend.tone;
  $("sum-trend-detail").textContent = trend.detail;

  const change = summary.period_change;
  const changeEl = $("sum-change");
  changeEl.textContent = formatSignedWon(change?.value);
  changeEl.dataset.tone = !change ? "none" : change.value > 0 ? "up" : change.value < 0 ? "down" : "flat";
  $("sum-change-pct").textContent = change
    ? `${change.pct >= 0 ? "+" : ""}${change.pct.toFixed(2)}% (첫 값 대비)`
    : "";
  $("sum-std").textContent = formatWon(summary.std_dev);
}

async function loadSummary() {
  try {
    renderSummary(await api.getSummary());
  } catch (error) {
    showToast(`요약을 불러오지 못했습니다: ${error.message}`);
  }
}

// ---------- 대화 기록 ----------

function markActiveConversation() {
  for (const item of $("conversation-list").children) {
    item.classList.toggle("active", item.dataset.id === state.conversationId);
  }
}

function renderConversations(conversations) {
  const list = $("conversation-list");
  list.replaceChildren();
  $("conversation-empty").hidden = conversations.length > 0;

  for (const conversation of conversations) {
    const item = createEl("li", "conversation-item");
    item.dataset.id = conversation.id;

    const open = createButton("", "conversation-open", () => openConversation(conversation.id));
    open.append(
      createEl("span", "conversation-title", conversation.title),
      createEl(
        "span",
        "conversation-meta",
        `${formatKst(conversation.updated_at)} · 메시지 ${conversation.message_count}개`,
      ),
    );
    const remove = createButton(
      "✕",
      "icon-btn",
      () => deleteConversation(conversation),
      `대화 삭제: ${conversation.title}`,
    );

    item.append(open, remove);
    list.append(item);
  }
  markActiveConversation();
}

async function loadConversations() {
  try {
    renderConversations(await api.listConversations());
  } catch (error) {
    showToast(`대화 목록을 불러오지 못했습니다: ${error.message}`);
  }
}

async function openConversation(id) {
  if (state.sending) return;
  try {
    const conversation = await api.getConversation(id);
    state.conversationId = conversation.id;
    $("chat-title").textContent = conversation.title;
    renderMessages(conversation.messages);
    markActiveConversation();
    switchTab("chat");
  } catch (error) {
    showToast(`대화를 불러오지 못했습니다: ${error.message}`);
  }
}

async function deleteConversation(conversation) {
  if (state.sending) return;
  if (!confirm(`"${conversation.title}" 대화를 삭제할까요?`)) return;
  try {
    await api.deleteConversation(conversation.id);
    if (state.conversationId === conversation.id) startNewChat();
    showToast("대화를 삭제했습니다.", "success");
    await loadConversations();
  } catch (error) {
    showToast(error.message);
  }
}

function startNewChat() {
  state.conversationId = null;
  $("chat-title").textContent = "새 대화";
  renderMessages([]);
  markActiveConversation();
  switchTab("chat");
  $("chat-input").focus();
}

// ---------- 채팅 ----------

function messageBubble(role, text) {
  const bubble = createEl("div", `message message-${role}`);
  bubble.append(
    createEl("span", "message-role", role === "user" ? "나" : "AI"),
    createEl("p", "message-text", text),
  );
  return bubble;
}

function loadingBubble() {
  const bubble = createEl("div", "message message-assistant loading");
  const text = createEl("p", "message-text", "답변을 작성하고 있어요");
  const dots = createEl("span", "dots");
  dots.setAttribute("aria-hidden", "true");
  dots.append(createEl("span"), createEl("span"), createEl("span"));
  text.append(dots);
  bubble.append(createEl("span", "message-role", "AI"), text);
  return bubble;
}

function scrollMessagesToBottom() {
  const box = $("messages");
  box.scrollTop = box.scrollHeight;
}

function renderMessages(messages) {
  const box = $("messages");
  box.replaceChildren();
  if (!messages.length) {
    box.append(emptyChat);
    return;
  }
  for (const message of messages) box.append(messageBubble(message.role, message.content));
  scrollMessagesToBottom();
}

function setSending(sending) {
  state.sending = sending;
  $("chat-input").disabled = sending;
  $("chat-send").disabled = sending;
  $("chat-send").textContent = sending ? "답변 대기 중…" : "보내기";
  $("new-chat").disabled = sending;
}

async function sendMessage(text) {
  const message = text.trim();
  if (!message || state.sending) return;

  const box = $("messages");
  if (emptyChat.isConnected) box.replaceChildren();
  const userBubble = messageBubble("user", message);
  const loading = loadingBubble();
  box.append(userBubble, loading);
  scrollMessagesToBottom();
  $("chat-input").value = "";
  setSending(true);

  try {
    const response = await api.chat(message, state.conversationId);
    loading.replaceWith(messageBubble("assistant", response.reply));
    state.conversationId = response.conversation_id;
    $("chat-title").textContent = response.title;
    renderSummary(response.summary);
    await loadConversations();
  } catch (error) {
    // 서버는 실패 시 아무것도 저장하지 않으므로 화면에서도 되돌리고 입력을 복원한다.
    userBubble.remove();
    loading.remove();
    if (!box.children.length) box.append(emptyChat);
    $("chat-input").value = message;
    showToast(error.message);
  } finally {
    setSending(false);
    scrollMessagesToBottom();
    $("chat-input").focus();
  }
}

// ---------- 데이터 관리 ----------

function renderDataRows(items) {
  const rows = $("data-rows");
  const fragment = document.createDocumentFragment();
  let flashRow = null;

  for (const item of items) {
    const row = createEl("tr");
    if (item.id === state.editingId) row.classList.add("editing");
    if (item.date === state.flashDate) {
      row.classList.add("flash");
      flashRow = row;
    }
    const actions = createEl("td", "actions");
    actions.append(
      createButton("수정", "btn btn-small", () => startEdit(item), `${item.date} 데이터 수정`),
      createButton("삭제", "btn btn-small btn-danger", () => deleteData(item), `${item.date} 데이터 삭제`),
    );
    row.append(
      createEl("td", "", item.date),
      createEl("td", "num", formatWon(item.value)),
      createEl("td", "memo", item.memo),
      actions,
    );
    fragment.append(row);
  }

  rows.replaceChildren(fragment);
  $("data-count").textContent = `(${items.length}개)`;
  if (flashRow) flashRow.scrollIntoView({ block: "nearest" });
  state.flashDate = null;
}

async function loadData() {
  try {
    const items = await api.listData(); // 서버가 날짜 오름차순으로 준다
    state.dataItems = items;
    renderDataRows(sortByDateDesc(items));
    renderChart(items);
  } catch (error) {
    showToast(`데이터를 불러오지 못했습니다: ${error.message}`);
  }
}

function exportData(format) {
  if (!state.dataItems.length) {
    showToast("내보낼 데이터가 없습니다.");
    return;
  }
  if (format === "csv") {
    // BOM을 붙여야 엑셀에서 한글이 깨지지 않는다.
    downloadText(`﻿${toCsv(state.dataItems)}`, exportFilename("csv"), "text/csv;charset=utf-8");
  } else {
    downloadText(toJson(state.dataItems), exportFilename("json"), "application/json");
  }
  showToast(`${state.dataItems.length}개 데이터를 ${format.toUpperCase()} 파일로 내보냈습니다.`, "success");
}

// ---------- 추세 그래프 (SVG, 라이브러리 없음) ----------

const SVG_NS = "http://www.w3.org/2000/svg";
const TOOLTIP_WIDTH = 176;
const TOOLTIP_HEIGHT = 48;
const axisFormat = new Intl.NumberFormat("ko-KR");
const clamp = (value, low, high) => Math.min(Math.max(value, low), high);

function svgEl(tag, attrs = {}, text) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderChart(items) {
  const container = $("chart");
  const model = buildChartModel(items);
  if (!model) {
    container.replaceChildren(createEl("p", "muted", "그래프를 그리려면 데이터가 2개 이상 필요합니다."));
    $("chart-desc").textContent = "";
    return;
  }

  const { width, height, padding, points } = model;
  const svg = svgEl("svg", {
    viewBox: `0 0 ${width} ${height}`,
    class: "chart-svg",
    role: "img",
    "aria-labelledby": "chart-title chart-desc",
  });

  for (const tick of model.yTicks) {
    svg.append(
      svgEl("line", { x1: padding.left, x2: width - padding.right, y1: tick.y, y2: tick.y, class: "chart-grid" }),
      svgEl(
        "text",
        { x: padding.left - 8, y: tick.y + 4, "text-anchor": "end", class: "chart-label" },
        axisFormat.format(tick.value),
      ),
    );
  }
  for (const tick of model.xTicks) {
    svg.append(
      svgEl("text", { x: tick.x, y: height - 10, "text-anchor": "middle", class: "chart-label" }, tick.label),
    );
  }
  if (model.maPath) svg.append(svgEl("path", { d: model.maPath, class: "chart-ma" }));
  svg.append(svgEl("path", { d: model.linePath, class: "chart-line" }));

  for (const [index, kind, label] of [
    [model.maxIndex, "max", "최고"],
    [model.minIndex, "min", "최저"],
  ]) {
    const point = points[index];
    svg.append(
      svgEl("circle", { cx: point.x, cy: point.y, r: 4.5, class: `chart-extreme ${kind}` }),
      svgEl(
        "text",
        {
          x: clamp(point.x, padding.left + 50, width - padding.right - 50),
          y: kind === "max" ? point.y - 10 : point.y + 18,
          "text-anchor": "middle",
          class: `chart-extreme-label ${kind}`,
        },
        `${label} ${formatWon(point.value)}`,
      ),
    );
  }

  // 마우스 위치에서 가장 가까운 날짜의 값을 보여주는 툴팁
  const hover = svgEl("g", { visibility: "hidden" });
  const hoverLine = svgEl("line", { y1: padding.top, y2: height - padding.bottom, class: "chart-hover-line" });
  const hoverDot = svgEl("circle", { r: 5, class: "chart-hover-dot" });
  const tipBox = svgEl("rect", { width: TOOLTIP_WIDTH, height: TOOLTIP_HEIGHT, rx: 6, class: "chart-tooltip-box" });
  const tipTitle = svgEl("text", { class: "chart-tooltip-text strong" });
  const tipDetail = svgEl("text", { class: "chart-tooltip-text" });
  hover.append(hoverLine, hoverDot, tipBox, tipTitle, tipDetail);
  svg.append(hover);

  const showPoint = (index) => {
    const point = points[index];
    const boxX =
      point.x + 12 + TOOLTIP_WIDTH > width - padding.right ? point.x - 12 - TOOLTIP_WIDTH : point.x + 12;
    const boxY = clamp(point.y - TOOLTIP_HEIGHT / 2, padding.top, height - padding.bottom - TOOLTIP_HEIGHT);
    hoverLine.setAttribute("x1", point.x);
    hoverLine.setAttribute("x2", point.x);
    hoverDot.setAttribute("cx", point.x);
    hoverDot.setAttribute("cy", point.y);
    tipBox.setAttribute("x", boxX);
    tipBox.setAttribute("y", boxY);
    tipTitle.setAttribute("x", boxX + 10);
    tipTitle.setAttribute("y", boxY + 19);
    tipTitle.textContent = `${point.date}  ${formatWon(point.value)}`;
    tipDetail.setAttribute("x", boxX + 10);
    tipDetail.setAttribute("y", boxY + 37);
    tipDetail.textContent = `${model.maWindow}일 평균 ${formatWon(point.average)}`;
    hover.setAttribute("visibility", "visible");
  };
  svg.addEventListener("pointermove", (event) => {
    const rect = svg.getBoundingClientRect();
    showPoint(nearestIndex(points, ((event.clientX - rect.left) / rect.width) * width));
  });
  svg.addEventListener("pointerleave", () => hover.setAttribute("visibility", "hidden"));

  container.replaceChildren(svg);

  const first = points[0];
  const last = points[points.length - 1];
  const high = points[model.maxIndex];
  const low = points[model.minIndex];
  $("chart-desc").textContent =
    `${first.date} ~ ${last.date} (${points.length}개). ` +
    `최고 ${formatWon(high.value)} (${high.date}), 최저 ${formatWon(low.value)} (${low.date}), ` +
    `최신 ${formatWon(last.value)}. 점선은 ${model.maWindow}일 이동평균입니다.`;
}

function startEdit(item) {
  state.editingId = item.id;
  $("data-date").value = item.date;
  $("data-value").value = item.value;
  $("data-memo").value = item.memo;
  $("data-form-title").textContent = `데이터 수정: ${item.date}`;
  $("data-submit").textContent = "수정 저장";
  $("data-cancel").hidden = false;
  for (const row of $("data-rows").children) row.classList.remove("editing");
  $("data-form").scrollIntoView({ block: "nearest" });
  $("data-value").focus();
}

function resetDataForm() {
  state.editingId = null;
  $("data-form").reset();
  $("data-form-title").textContent = "새 데이터 추가";
  $("data-submit").textContent = "추가";
  $("data-cancel").hidden = true;
  for (const row of $("data-rows").children) row.classList.remove("editing");
}

async function submitData(event) {
  event.preventDefault();
  const payload = {
    date: $("data-date").value,
    value: Number($("data-value").value),
    memo: $("data-memo").value.trim(),
  };
  const editing = state.editingId;
  $("data-submit").disabled = true;

  try {
    if (editing) {
      await api.updateData(editing, payload);
      showToast(`${payload.date} 데이터를 수정했습니다.`, "success");
    } else {
      await api.createData(payload);
      showToast(`${payload.date} 데이터를 추가했습니다.`, "success");
    }
    resetDataForm();
    state.flashDate = payload.date;
    await Promise.all([loadData(), loadSummary()]);
  } catch (error) {
    showToast(error.message);
  } finally {
    $("data-submit").disabled = false;
  }
}

async function deleteData(item) {
  if (!confirm(`${item.date} 데이터(${formatWon(item.value)})를 삭제할까요?`)) return;
  try {
    await api.deleteData(item.id);
    if (state.editingId === item.id) resetDataForm();
    showToast(`${item.date} 데이터를 삭제했습니다.`, "success");
    await Promise.all([loadData(), loadSummary()]);
  } catch (error) {
    showToast(error.message);
  }
}

// ---------- 탭 / 이벤트 ----------

function switchTab(name) {
  for (const tab of ["chat", "data", "chart"]) {
    const selected = tab === name;
    $(`tab-${tab}`).setAttribute("aria-selected", String(selected));
    $(`panel-${tab}`).hidden = !selected;
  }
}

function bindEvents() {
  $("tab-chat").addEventListener("click", () => switchTab("chat"));
  $("tab-data").addEventListener("click", () => switchTab("data"));
  $("tab-chart").addEventListener("click", () => switchTab("chart"));
  $("new-chat").addEventListener("click", startNewChat);
  $("export-csv").addEventListener("click", () => exportData("csv"));
  $("export-json").addEventListener("click", () => exportData("json"));
  initThemeToggle($("theme-toggle"));

  $("chat-form").addEventListener("submit", (event) => {
    event.preventDefault();
    sendMessage($("chat-input").value);
  });
  $("chat-input").addEventListener("keydown", (event) => {
    // 한글 입력 조합 중(isComposing)에는 Enter로 전송하지 않는다.
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      sendMessage($("chat-input").value);
    }
  });
  for (const chip of document.querySelectorAll(".chip")) {
    chip.addEventListener("click", () => sendMessage(chip.dataset.question));
  }

  $("data-form").addEventListener("submit", submitData);
  $("data-cancel").addEventListener("click", resetDataForm);
}

async function init() {
  bindEvents();
  try {
    await wakeServer();
    setServerStatus("online", "서버 연결됨");
  } catch {
    setServerStatus("offline", "서버 연결 실패");
    showToast("서버에 연결할 수 없습니다. 잠시 후 새로고침하세요.");
    return;
  }
  await Promise.all([loadSummary(), loadConversations(), loadData()]);
}

init();
