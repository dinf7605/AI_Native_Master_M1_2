# Plan: 데이터 확보 & 분석 (USD/KRW 환율)

**Source PRD**: `.claude/prds/fx-data-ai-chat.prd.md`
**Selected Milestone**: #1 데이터 확보 & 분석
**Complexity**: Small

## Summary
USD/KRW 일별 환율 100+ 포인트를 `(date, value, memo)` CSV로 확보한다. 이 데이터로 요약 정보(기간·개수·평균/최대/최소·최근 추세)를 만드는 순수 함수를 구현하고 테스트로 검증한다. 이 함수는 이후 마일스톤 2(`GET /api/data/summary`)와 4(시스템 프롬프트 주입)가 그대로 재사용한다. 이 단계는 Firestore나 OpenAI에 의존하지 않는다.

## Decisions (PRD Open Questions 중 이 마일스톤에서 확정)
| 질문 | 결정 | 근거 |
|---|---|---|
| 어떤 시계열인가 | **USD/KRW 일별 환율** (ECB 기준환율) | API 키 없이 받을 수 있음 (실제 호출로 확인). 추세가 뚜렷함 |
| 데이터 출처 | Frankfurter API `https://api.frankfurter.dev/v1/{start}..{end}?base=USD&symbols=KRW` | 무료, 키 불필요, JSON |
| 기간 | 2026-03-02 ~ 2026-09-24 (영업일만 약 140개) | ≥100 조건을 여유 있게 충족하면서 Firestore 읽기량은 작게 유지 |
| 결측(주말·공휴일) | 보간하지 않고 영업일만 저장 | 실제 관측값만 사용. 추세는 포인트 개수 기준으로 계산 |
| 초기 적재 경로 | 이번엔 CSV 생성까지만. Firestore 적재는 마일스톤 2 | 마일스톤 범위 분리 |
| "최근 추세" 정의 | 최근 7포인트 평균과 그 직전 7포인트 평균의 변화율. \|변화율\| < 0.5%면 `flat`, 양수면 `increase`, 음수면 `decrease` | FX 주간 변동폭 기준. 창 크기와 임계값은 파라미터로 둠 |
| 같은 date 중복 | 분석 함수는 날짜순 정렬만 하고 중복은 허용. 중복 방지는 마일스톤 2의 API 검증에서 결정 | 이 단계에선 입력이 통제된 CSV |

## Patterns to Mirror
| Category | Source | Pattern |
|---|---|---|
| Naming | — | 기존 코드 없음 (빈 저장소). PEP 8 snake_case, 모듈은 역할 기준(`services/`, `scripts/`)으로 새로 정한다 |
| Errors | — | 기존 패턴 없음. 스크립트는 네트워크/응답 오류 시 메시지와 함께 non-zero 종료, 분석 함수는 빈 입력에 예외 대신 `count=0` 요약 반환 |
| Tests | — | 기존 패턴 없음. `backend/tests/test_*.py` + pytest, 네트워크 없는 순수 함수 테스트 |

## Target Layout (이번 마일스톤에서 생기는 부분만)
```
backend/
  app/
    __init__.py
    services/
      __init__.py
      analysis.py        # build_summary(records) — 순수 함수
  scripts/
    fetch_fx_data.py     # Frankfurter → data/usdkrw.csv (표준 라이브러리만 사용)
  data/
    usdkrw.csv           # date,value,memo
  tests/
    test_analysis.py
  requirements.txt       # 과제 지정 5개 패키지
  requirements-dev.txt   # pytest
  .env.example           # 키 이름만 (값 없음)
.gitignore               # .venv, .env, *service-account*.json, __pycache__
```
마일스톤 2에서 `app/main.py`, `app/routers/`, `app/schemas/`가 같은 트리에 추가될 예정이다.

## Files to Change
| File | Action | Why |
|---|---|---|
| `.gitignore` | CREATE | venv, `.env`, 서비스 계정 키 파일이 커밋되지 않도록 처음부터 차단 |
| `backend/requirements.txt` | CREATE | fastapi, uvicorn, firebase-admin, openai, python-dotenv (과제 지정) |
| `backend/requirements-dev.txt` | CREATE | pytest (배포 이미지에서는 제외) |
| `backend/.env.example` | CREATE | `OPENAI_API_KEY`, `FIREBASE_SERVICE_ACCOUNT_JSON`, `ALLOWED_ORIGINS` 이름만 기재 |
| `backend/scripts/fetch_fx_data.py` | CREATE | 환율 데이터 수집 후 CSV 저장 (재현 가능한 데이터 준비) |
| `backend/data/usdkrw.csv` | CREATE | 스크립트 실행 결과. 약 140행 |
| `backend/app/__init__.py`, `backend/app/services/__init__.py` | CREATE | 패키지 선언 |
| `backend/app/services/analysis.py` | CREATE | 요약 계산 로직 (API/프롬프트에서 재사용) |
| `backend/tests/test_analysis.py` | CREATE | 요약 로직 단위 테스트 |
| `.claude/prds/fx-data-ai-chat.prd.md` | UPDATE | 마일스톤 1 상태를 `in-progress`로 변경하고 plan 링크 추가 (완료됨) |

## Tasks

### Task 1: 프로젝트 골격 + venv
- **Action**: 위 레이아웃의 디렉터리, `.gitignore`, `requirements*.txt`, `.env.example`을 만든다. `backend/.venv`에 Python 3.13 가상환경을 만들고 의존성을 설치한다.
- **Mirror**: 없음 (신규)
- **Validate**: `backend/.venv/Scripts/python -c "import fastapi, uvicorn, firebase_admin, openai, dotenv; print('ok')"`

### Task 2: 요약 로직 테스트 먼저 작성 (RED)
- **Action**: `tests/test_analysis.py`에 아래 케이스를 작성한다.
  - 빈 리스트면 `count == 0`이고 통계와 추세는 `None`, trend는 `"insufficient_data"`
  - 정렬되지 않은 입력이면 `start_date`와 `end_date`가 날짜순 최소/최대
  - mean/min/max 값과 해당 날짜가 정확 (소수 2자리 반올림)
  - 상승 시계열(마지막 7개 평균이 직전 7개보다 1% 이상 높음)은 `increase`
  - 하락 시계열은 `decrease`
  - 변화 < 0.5%는 `flat`
  - 포인트 < 14개면 창 크기를 `count // 2`로 줄여 계산하고, count < 2면 `insufficient_data`
  - `latest`가 가장 최근 날짜의 값
- **Mirror**: 없음 (신규)
- **Validate**: `pytest backend/tests -q` → import/assert 실패 확인

### Task 3: `build_summary` 구현 (GREEN)
- **Action**: `analysis.py`에 `build_summary(records, window=7, flat_threshold_pct=0.5) -> dict`를 구현한다.
  - 입력: `date`(ISO 문자열)와 `value`(float)를 가진 dict 목록. 표준 라이브러리 `statistics`만 사용한다.
  - 출력 스키마 (마일스톤 2의 Pydantic 응답 모델이 이 형태를 따른다):
    ```json
    {
      "count": 140,
      "start_date": "2026-03-02", "end_date": "2026-09-24",
      "mean": 1432.15,
      "min": {"value": 1398.2, "date": "..."},
      "max": {"value": 1471.9, "date": "..."},
      "latest": {"value": 1420.5, "date": "2026-09-24"},
      "trend": {"direction": "increase|decrease|flat|insufficient_data",
                "change_pct": 0.84, "window": 7}
    }
    ```
- **Mirror**: Task 2 테스트
- **Validate**: `pytest backend/tests -q` 전부 통과

### Task 4: 데이터 수집 스크립트
- **Action**: `scripts/fetch_fx_data.py`를 작성한다. `urllib.request`로 Frankfurter를 호출하고(추가 패키지 없음), 기간은 CLI 인자로 받되 기본값은 위 결정값을 쓴다.
  - 응답의 `rates`를 날짜순으로 `date,value,memo` CSV에 쓴다. memo는 `"ECB reference rate (Frankfurter)"`.
  - HTTP 오류, 빈 응답, 100건 미만이면 stderr에 이유를 출력하고 exit 1.
- **Mirror**: Errors 패턴 (위 표)
- **Validate**: `python backend/scripts/fetch_fx_data.py` 실행 후 `usdkrw.csv` 행 수 ≥ 100 확인

### Task 5: 실데이터 요약 산출 확인
- **Action**: CSV를 읽어 `build_summary`에 넣은 결과를 출력하는 원라이너(또는 스크립트의 `--summary` 플래그)로 실데이터 요약을 확인한다. 이 값이 README "데이터 분석" 절과 채팅 검증(PRD 성공지표 5/5)의 기준값이 된다.
- **Mirror**: —
- **Validate**: 출력된 count ≥ 100, 기간, 통계, 추세가 CSV를 육안으로 봤을 때와 모순 없음

## Validation
```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt -r requirements-dev.txt
.venv/Scripts/python scripts/fetch_fx_data.py
.venv/Scripts/python -m pytest tests -q
.venv/Scripts/python -c "import csv; from app.services.analysis import build_summary; r=list(csv.DictReader(open('data/usdkrw.csv',encoding='utf-8'))); r=[{**x,'value':float(x['value'])} for x in r]; s=build_summary(r); assert s['count']>=100; print(s)"
```

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| Frankfurter API 장애 또는 URL 변경 | Low | CSV를 저장소에 커밋해 이후 단계가 API에 의존하지 않게 함. 대체 출처는 yfinance `KRW=X` (추가 패키지 필요, 비상시에만) |
| Render 기본 Python 버전과 로컬 3.13 불일치 | Med | 마일스톤 7에서 Render `PYTHON_VERSION`을 3.13으로 고정. 이번엔 3.13 전용 문법을 쓰지 않음 (3.10+ 호환) |
| 추세 기준(7포인트/0.5%)이 실데이터에서 늘 `flat`으로 나옴 | Med | 파라미터화해 두고, Task 5 결과를 보고 조정. 조정값은 README에 기록 |
| 부동소수 반올림으로 테스트가 흔들림 | Low | 반올림 후 비교하거나 `pytest.approx` 사용 |

## Acceptance
- [x] `backend/data/usdkrw.csv`에 USD/KRW 100개 이상 저장 (`date,value,memo`): **146행**
- [x] `build_summary`가 기간, 개수, 평균, 최대, 최소, 최신값, 추세를 반환
- [x] 단위 테스트 전부 통과 (네트워크 없이): **10 passed**
- [x] 비밀값 없음. `.gitignore`가 `.env`와 키 파일을 차단
- [x] Patterns mirrored, not reinvented (신규 저장소라 이 마일스톤이 기준 패턴을 정함)

## Result (2026-09-25 실행)
실데이터 요약 기준값이다. README와 채팅 검증(PRD 성공지표 5/5)에서 대조할 때 사용한다.

| 항목 | 값 |
|---|---|
| 기간 | 2026-03-02 ~ 2026-09-24 |
| 개수 | 146 |
| 평균 | 1466.60 |
| 최소 | 1336.20 (2026-09-09) |
| 최대 | 1558.09 (2026-07-01) |
| 최신 | 1368.60 (2026-09-24) |
| 추세 | increase, +1.94% (최근 7개 평균 1371.53, 직전 7개 평균 1345.40) |

- 추세 값은 수동 계산과 일치한다. 기준(7포인트/0.5%)은 실데이터에서 의미 있는 결과를 내므로 조정하지 않았다.
- 계획과 다른 점: `backend/pytest.ini`를 추가했다 (`pythonpath = .`로 `app` 패키지 import). `tests/__init__.py`는 만들지 않았다.
- 참고: 전체 기간으로 보면 7월 고점 후 하락했고, 최근 2주는 반등 중이다. "최근 추세"는 단기 신호라서, 장기 흐름(고점 대비 하락)은 마일스톤 6의 추가 지표(예: 기간 변화율)로 보완할 수 있다.
