// 다크 모드 토글. 첫 테마는 index.html <head>의 인라인 스크립트가 첫 페인트 전에 정한다(깜빡임 방지).

const STORAGE_KEY = "theme";

function currentTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function applyTheme(theme, button) {
  document.documentElement.dataset.theme = theme;
  button.textContent = theme === "dark" ? "☀️ 라이트 모드" : "🌙 다크 모드";
}

export function initThemeToggle(button) {
  applyTheme(currentTheme(), button);
  button.addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    applyTheme(next, button);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // 저장이 막힌 환경(시크릿 창 등)에서는 이번 방문에만 적용한다.
    }
  });
}
