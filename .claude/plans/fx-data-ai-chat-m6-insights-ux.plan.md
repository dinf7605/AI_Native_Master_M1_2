# Plan: 인사이트·UX 보너스

**Source PRD**: `.claude/prds/fx-data-ai-chat.prd.md`
**Selected Milestone**: #6 인사이트·UX 보너스
**Complexity**: Medium

## Summary
과제 보너스 "인사이트·UX 고도화" 네 항목을 구현한다.
1. 요약에 추가 지표 2개 (표준편차, 기간 전체 변화)
2. SVG 추세 그래프 (환율 + 7일 이동평균, 마우스 툴팁)
3. CSV/JSON 내보내기
4. 다크 모드 토글

추가 지표는 AI 프롬프트에도 들어간다. 그래서 AI가 "최근 단기 반등"뿐 아니라 "기간 전체로는 하락"이라는 장기 흐름도 함께 설명할 수 있다 (마일스톤 1에서 남긴 보완점).

## Decisions
| 질문 | 결정 | 근거 |
|---|---|---|
| 지표 위치 | `/api/data/summary`를 보강한다: `std_dev`(표본 표준편차), `period_change: {value, pct}`(첫 값 → 최신 값). 2개 미만이면 null | 별도 엔드포인트 없이 채팅 주입과 화면 표시에 그대로 쓰임 |
| 그래프 | 라이브러리 없이 SVG를 직접 그린다 (`createElementNS`, innerHTML 미사용). 좌표 계산은 순수 함수 `chart.js`로 분리해 node 테스트 | 과제 "프레임워크 금지"를 확실히 지킴. 좌표 로직은 테스트 가능 |
| 그래프 내용 | 환율 선 + 7일 이동평균 점선, y축 눈금 4~6개(1·2·5 단위), x축은 월 시작일, 최고·최저 점 표시, 마우스 위치에 가장 가까운 날짜의 값 툴팁. 제목/설명(aria)도 제공 | 추세·변화를 한눈에 봄. 접근성 |
| 그래프 위치 | 탭 추가 [채팅 \| 데이터 관리 \| 추세 그래프]. 데이터 변경 시 다시 그림 | 채팅 화면 높이를 줄이지 않음 |
| 내보내기 | 데이터 관리 탭의 "CSV 다운로드", "JSON 다운로드". 클라이언트에서 현재 목록(날짜 오름차순)을 Blob으로 저장. CSV는 UTF-8 BOM(엑셀 한글), RFC 4180 따옴표 처리, `= + - @`로 시작하는 메모 앞에 `'`를 붙여 수식 실행(CSV 인젝션) 차단. 파일명 `usdkrw-data-YYYYMMDD.csv` | 서버 부담 없음. 보안 |
| 다크 모드 | 헤더 토글 버튼. `html[data-theme]`로 색 변수를 교체. 첫 방문은 `prefers-color-scheme`을 따르고, 선택은 localStorage에 저장 (접근 실패 시 무시). `<head>` 인라인 스크립트로 첫 페인트 전에 적용해 깜빡임을 막음 | 이미 모든 색이 CSS 변수라 변수만 재정의 |

## Files to Change
| File | Action | Why |
|---|---|---|
| `backend/app/services/analysis.py` | UPDATE | `std_dev`, `period_change` |
| `backend/app/schemas/data.py` | UPDATE | `SummaryResponse`에 필드 추가 |
| `backend/app/prompts.py` | UPDATE | 요약 문장에 변동성·기간 변화 추가 |
| `backend/tests/test_analysis.py`, `test_prompts.py`, `test_data_api.py` | UPDATE | 새 지표 테스트 |
| `frontend/js/chart.js` | CREATE | 이동평균, 눈금, 좌표 계산 (순수) |
| `frontend/js/export.js` | CREATE | CSV/JSON 문자열 생성 (순수) + 다운로드 |
| `frontend/js/theme.js` | CREATE | 다크 모드 토글 |
| `frontend/js/format.js` | UPDATE | 부호 있는 금액 포맷 |
| `frontend/js/app.js`, `index.html`, `css/styles.css` | UPDATE | 카드 2개, 그래프 탭, 내보내기 버튼, 토글, 다크 색 |
| `frontend/tests/chart.test.js`, `export.test.js`, `format.test.js` | CREATE/UPDATE | 순수 함수 테스트 |

## Tasks
1. 백엔드 테스트 먼저 → `build_summary` 보강 → 스키마·프롬프트 반영
2. 프론트 순수 함수 테스트 먼저 (chart, export, format) → 구현
3. 화면: 요약 카드 2개, 그래프 탭(SVG 렌더링과 툴팁), 내보내기 버튼, 다크 모드
4. 브라우저 확인:
   - 그래프가 그려지고 툴팁이 뜨는지
   - 데이터를 수정하면 그래프가 갱신되는지
   - CSV/JSON 내용과 행 수
   - 다크 모드 전환과 새로고침 후 유지
   - 모바일 폭
   - 새 지표를 반영한 채팅 답변 1회 ("장기 흐름은?")

## Validation
```bash
cd backend && .venv/Scripts/python -m pytest -q
cd frontend && npm test
```

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| 요약 응답 필드 추가로 기존 클라이언트 영향 | Low | 필드 추가만 하고 기존 필드는 그대로 둔다 |
| SVG 크기 반응형 | Med | `viewBox` 고정 좌표 + CSS 너비 100%, 툴팁 좌표는 viewBox 기준으로 변환 |
| localStorage 차단 환경 | Low | try/catch, 실패 시 시스템 설정만 따름 |
| CSV를 엑셀에서 열 때 한글 깨짐, 수식 실행 | Med | BOM, 위험 문자 앞에 `'` |

## Acceptance
- [x] `/api/data/summary`에 `std_dev`, `period_change`가 있고 Swagger에 보인다
- [x] 채팅 답변이 장기 흐름(기간 변화)을 반영할 수 있다
- [x] 그래프: 환율 선, 이동평균, 축, 툴팁. 데이터 변경 시 갱신
- [x] CSV/JSON 다운로드 (146행, 한글·특수문자 안전)
- [x] 다크 모드 토글, 새로고침 후 유지, 깜빡임 없음
- [x] 백엔드·프론트 테스트 전부 통과 (백엔드 97, 프론트 24)

## Result (2026-09-25)
- **추가 지표**: 기간 전체 변화 **-93.51원 (-6.40%)**, 표준편차 **57.41원**. 요약 카드 2개를 추가했고, 하락은 파랑으로 표시한다
- **AI 반영**: "기간 전체 흐름은?"에 "전체 -6.40% 하락, 최근 단기는 +1.94% 반등"으로 두 관점을 구분해 답했다 (마일스톤 1의 보완점 해소)
- **그래프**:
  - SVG로 146개 점, 7일 이동평균(140개), y축 1,300~1,600, 3~9월 라벨
  - 최고(7/1)와 최저(9/9) 표시
  - 최고점에 마우스를 올리면 "2026-07-01 1,558.09원 / 7일 평균 1,544.96원"
  - 데이터를 추가하면 147개 점, 최고 라벨이 1,600원으로 바뀌고, 삭제하면 146개로 돌아온다
- **내보내기**:
  - CSV: 헤더 + 146행, 파일 첫 바이트 `ef bb bf`(BOM 확인)
  - JSON: 146개, id 제외
  - 파일명 `usdkrw-data-20260925.*`
- **다크 모드**: 배경과 그래프 색이 전환되고 localStorage에 저장된다. 새로고침 후에도 유지된다
- **E2E 중 발견해 수정한 버그 3건**:
  1. **Firebase 초기화 경쟁 조건 (백엔드)**
     - 증상: 서버 시작 직후 동시에 들어온 첫 요청들이 500으로 실패했다 (브라우저에는 CORS 오류로 보임)
     - 영향: Render 콜드스타트마다 재현될 문제였다
     - 조치: `threading.Lock` + 이중 확인으로 수정하고, 동시성 재현 테스트(`test_firebase.py`)를 추가했다
  2. **탭 전환 시 채팅 패널이 계속 보임 (마일스톤 5부터 있던 버그)**
     - 원인: `.chat-panel { display: flex }`가 `hidden` 속성을 덮어썼다
     - 조치: 전역 `[hidden] { display: none !important }`
  3. **모바일 가로 넘침**
     - 원인 1: 헤더 버튼이 늘어나 줄바꿈 없이 넘쳤다
     - 원인 2: 긴 대화 제목(nowrap)이 그리드 열의 최소 너비를 넓혔다
     - 조치: 헤더 `flex-wrap`, 그리드 `minmax(0, 1fr)`. 긴 제목 상태에서 3개 탭 모두 375px에 맞는 것을 확인했다
- 테스트용 데이터와 대화는 정리했고, 테마는 라이트로 되돌렸다
