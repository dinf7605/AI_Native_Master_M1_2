# Plan: 데이터 API (Firestore)

**Source PRD**: `.claude/prds/fx-data-ai-chat.prd.md`
**Selected Milestone**: #2 데이터 API (Firestore)
**Complexity**: Medium

## Summary
FastAPI 앱을 초기화(CORS, `/docs`)하고, Firestore `data` 컬렉션을 대상으로 CRUD 4개와 `GET /api/data/summary`를 구현한다. 요청은 Pydantic으로 검증한다. 구조는 router(HTTP) → service(비즈니스 규칙) → repository(Firestore 접근)로 나눈다. 테스트는 repository를 인메모리 가짜로 바꿔 네트워크 없이 돌린다. 마지막으로 마일스톤 1의 CSV 146행을 Firestore에 적재하고, summary 결과가 마일스톤 1 기준값과 같은지 확인한다.

## Decisions
| 질문 | 결정 | 근거 |
|---|---|---|
| 실행 진입점 | `backend/main.py`의 `app` → `uvicorn main:app --reload` | 과제 명세의 실행 예시와 동일 |
| 계층 분리 | `routers/` → `services/` → `repositories/` | 과제 학습목표("라우터/서비스 분리 기준 설명"). repository를 분리하면 Firestore 없이 테스트 가능 |
| Firestore 문서 형태 | `data/{자동ID}` = `{date: "YYYY-MM-DD", value: float, memo: str, created_at, updated_at}` | date를 ISO 문자열로 저장하면 사전순 정렬이 곧 날짜순 (`order_by("date")`) |
| 같은 date 중복 | **거부 (409 Conflict)**. 생성·수정 시 다른 문서가 같은 date를 가지면 실패 | 하루 1개 환율이라는 데이터 의미 유지, 요약·그래프 왜곡 방지 |
| PUT 의미 | 전체 교체 (date, value, memo 모두 필요) | REST 관례. 부분 수정(PATCH)은 범위 밖 |
| 입력 검증 | `date`: 날짜 타입. `value`: 0 초과 유한수 (NaN/inf 거부). `memo`: 0~200자, 앞뒤 공백 제거. 정의되지 않은 필드는 거부 | 환율은 양수. 과제 "입력 값 검증" 요건 |
| 인증 정보 로드 | `FIREBASE_SERVICE_ACCOUNT_JSON`(JSON 문자열)이 있으면 우선 사용, 없으면 `FIREBASE_SERVICE_ACCOUNT_PATH` 파일 | 로컬은 파일, Render는 환경 변수 |
| 설정 누락/DB 오류 | 앱은 뜨고 `/docs`도 보인다. DB가 필요한 요청만 503과 한국어 메시지로 응답 (키 내용은 노출 안 함) | 배포 직후 설정 실수를 진단하기 쉬움 |
| 초기 데이터 적재 | `scripts/seed_firestore.py`가 CSV를 읽어 이미 있는 date는 건너뛰고 batch로 쓴다 (여러 번 실행해도 안전) | PRD Open Question "초기 적재 경로" 해소 |
| 헬스체크 | `GET /health` → `{"status": "ok"}` (DB 접근 없음) | 마일스톤 5·7에서 Render 콜드스타트 깨우기용 |

## Patterns to Mirror
| Category | Source | Pattern |
|---|---|---|
| Naming | `backend/app/services/analysis.py:17` | snake_case 함수, 모듈 docstring으로 역할 설명, 상수는 모듈 상단 대문자 |
| Errors | `backend/scripts/fetch_fx_data.py:31` | 사용자에게 보이는 원인 메시지. 빈 입력은 예외 대신 정상 응답 (`build_summary([])` → count 0) |
| Tests | `backend/tests/test_analysis.py:8` | pytest, 헬퍼로 합성 레코드 생성, 한 테스트에 한 동작, `pytest.approx` |
| Data access | — | 기존 없음. 이 마일스톤에서 repository 패턴을 새로 정한다 |

## Target Layout (추가분)
```
backend/
  main.py                      # FastAPI 앱, CORS, 라우터 등록, 예외 핸들러, /health
  app/
    config.py                  # .env 로드, ALLOWED_ORIGINS 파싱, 인증 정보 선택
    firebase.py                # firebase_admin 1회 초기화, Firestore client 제공
    errors.py                  # NotFoundError, DuplicateDateError, DatabaseUnavailableError
    schemas/data.py            # DataCreate, DataItem, SummaryResponse
    repositories/data_repository.py  # FirestoreDataRepository
    services/data_service.py   # 중복 검사, 존재 확인, summary 계산(analysis 재사용)
    routers/data.py            # /api/data 엔드포인트 5개
  scripts/seed_firestore.py    # CSV → Firestore (멱등)
  tests/
    fakes.py                   # InMemoryDataRepository
    test_config.py
    test_data_schemas.py
    test_data_api.py           # TestClient + dependency override
```

## Files to Change
| File | Action | Why |
|---|---|---|
| `backend/requirements-dev.txt` | UPDATE | `httpx` 추가 (FastAPI TestClient 의존) |
| `backend/main.py` | CREATE | 앱 진입점, CORS, 라우터, 예외 → HTTP 상태코드 매핑 |
| `backend/app/config.py` | CREATE | 환경 변수 단일 진입점 |
| `backend/app/firebase.py` | CREATE | Firestore 연결 (지연 초기화) |
| `backend/app/errors.py` | CREATE | 도메인 예외 |
| `backend/app/schemas/__init__.py`, `data.py` | CREATE | Pydantic 요청/응답 모델 |
| `backend/app/repositories/__init__.py`, `data_repository.py` | CREATE | Firestore CRUD |
| `backend/app/services/data_service.py` | CREATE | 비즈니스 규칙 |
| `backend/app/routers/__init__.py`, `data.py` | CREATE | HTTP 엔드포인트 |
| `backend/scripts/seed_firestore.py` | CREATE | 초기 데이터 적재 |
| `backend/tests/fakes.py`, `test_config.py`, `test_data_schemas.py`, `test_data_api.py` | CREATE | 테스트 |
| `.claude/prds/fx-data-ai-chat.prd.md` | UPDATE | 마일스톤 2 상태/plan 링크 (완료) |

## Tasks

### Task 1: 설정 + Firestore 연결
- **Action**:
  - `config.py`: `load_dotenv(backend/.env)`. `get_allowed_origins()`는 쉼표로 나누고 공백·빈 항목을 제거한다. `load_firebase_credentials()`는 JSON 문자열을 우선 쓰고, 없으면 파일 경로, 둘 다 없으면 `DatabaseUnavailableError`.
  - `firebase.py`: `get_firestore_client()`. `firebase_admin._apps`로 중복 초기화를 막는다.
- **Mirror**: Errors 패턴
- **Validate**: `test_config.py` 작성 후 통과
  - origins 파싱
  - JSON 우선순위
  - 둘 다 없으면 예외 (monkeypatch로 환경 변수 조작)

### Task 2: Pydantic 스키마 (RED → GREEN)
- **Action**: `DataCreate(date: date, value: float, memo: str = "")`
  - `value`: `gt=0`, `allow_inf_nan=False`
  - `memo`: `max_length=200`, strip
  - `extra="forbid"`
  - 응답 모델: `DataItem`(id, date, value, memo), `SummaryResponse`(`build_summary` 출력 형태 그대로), `MessageResponse`
- **Mirror**: Tests 패턴
- **Validate**: `test_data_schemas.py`
  - 정상 입력
  - 잘못된 날짜 형식
  - value 0, 음수, 문자열
  - memo 201자
  - 알 수 없는 필드 → `ValidationError`

### Task 3: Repository
- **Action**: `FirestoreDataRepository(client)` 메서드:
  - `list_all()` (date 오름차순)
  - `get(id)`
  - `find_by_date(date)`
  - `create(dict)` (id 반환, `created_at`/`updated_at`은 `SERVER_TIMESTAMP`)
  - `update(id, dict)`
  - `delete(id)`

  `tests/fakes.py`의 `InMemoryDataRepository`가 같은 메서드를 구현한다.
- **Mirror**: —
- **Validate**: Task 4·5 테스트가 fake로 통과하는지, Task 6 실데이터 적재로 Firestore 구현을 확인

### Task 4: Service
- **Action**: `DataService(repo)` 메서드:
  - `list()`
  - `create(payload)`: 같은 date가 있으면 `DuplicateDateError`
  - `update(id, payload)`: 없으면 `NotFoundError`. 다른 문서가 같은 date면 `DuplicateDateError`
  - `delete(id)`: 없으면 `NotFoundError`
  - `summary()`: `build_summary(repo.list_all())`
- **Mirror**: `analysis.py` 재사용 (요약 로직 중복 금지)
- **Validate**: Task 5의 API 테스트로 검증

### Task 5: Router + 앱 (RED → GREEN)
- **Action**:
  - `routers/data.py`:
    - `POST /api/data` → 201 + `DataItem`
    - `GET /api/data` → `list[DataItem]`
    - `PUT /api/data/{id}` → `DataItem`
    - `DELETE /api/data/{id}` → `MessageResponse`
    - `GET /api/data/summary` → `SummaryResponse`
    - 모든 엔드포인트에 `summary`/`description`을 적어 Swagger에 한국어 설명이 보이게 한다.
  - `main.py`:
    - `CORSMiddleware(allow_origins=get_allowed_origins())`
    - 예외 매핑: `NotFoundError`→404, `DuplicateDateError`→409, `DatabaseUnavailableError`와 Google API 오류→503
    - `/health`
- **Mirror**: Tests 패턴
- **Validate**: `test_data_api.py` (TestClient, `app.dependency_overrides`로 fake 주입)
  - 생성 201, 중복 409, 검증 실패 422
  - 목록이 날짜순
  - 수정 200 / 없는 id 404 / 다른 문서 날짜로 수정 409
  - 삭제 200 / 404
  - summary가 데이터 변경을 반영
  - `/health` 200
  - CORS preflight에 허용 origin 헤더가 오는지

### Task 6: 초기 데이터 적재 (실제 Firestore)
- **Action**: `scripts/seed_firestore.py`
  - CSV를 읽고, `DataCreate`로 행 단위 검증한다.
  - Firestore에 이미 있는 date는 건너뛴다.
  - 최대 500건 batch로 쓴다.
  - 결과로 "추가 N / 건너뜀 M"을 출력한다.
  - `--dry-run`을 지원한다.
- **Mirror**: `fetch_fx_data.py`의 CLI/에러 스타일
- **Validate**: 1회 실행 → 추가 146. 2회 실행 → 추가 0 / 건너뜀 146

### Task 7: 로컬 통합 확인
- **Action**:
  - `uvicorn main:app --reload`로 서버를 띄운다.
  - `/docs` 페이지가 열리는지 확인한다.
  - curl로 생성 → 목록 → 수정 → 삭제 한 바퀴를 돈다. 테스트용 날짜 `2026-09-25`를 쓰고 끝나면 삭제한다.
  - `/api/data/summary`가 마일스톤 1 기준값과 같은지 본다: count 146, mean 1466.60, increase +1.94%.
- **Mirror**: —
- **Validate**: 아래 Validation 섹션

## Validation
```bash
cd backend
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest -q
.venv/Scripts/python scripts/seed_firestore.py --dry-run
.venv/Scripts/python scripts/seed_firestore.py
.venv/Scripts/uvicorn main:app --reload
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/data/summary
curl -X POST http://127.0.0.1:8000/api/data -H "Content-Type: application/json" -d "{\"date\":\"2026-09-25\",\"value\":1370.5,\"memo\":\"test\"}"
```

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| Firestore API 활성화 전파 지연 (현재 403) | Med | 콘솔에서 DB 생성 확인. Task 1~5는 fake로 진행 가능하므로 막히지 않음 |
| 중복 검사(조회 후 쓰기)가 동시 요청에서 경합 | Low | 단일 사용자 데모라 허용. 필요하면 트랜잭션으로 보강 (범위 밖) |
| summary 호출마다 전체 문서 읽기 (146 reads) | Low | 무료 한도(5만 reads/일) 안. 채팅(마일스톤 4)에서 호출 빈도가 늘면 캐시 검토 |
| `firebase_admin` 중복 초기화 오류 (uvicorn reload) | Med | `_apps` 확인 후 1회만 초기화 |
| CORS `*`로 두면 과제 보안 요건 위반 | Low | 명시적 origin 목록만 허용. 기본값은 로컬 개발 주소 |

## Acceptance
- [x] 서버가 실행되고 `/docs`에서 5개 엔드포인트와 한국어 설명이 보인다 (+ `/health`)
- [x] CRUD 4개 + summary가 실제 Firestore에서 동작한다
- [x] 잘못된 입력 422, 없는 id 404, 중복 date 409 (생성·수정 모두), DB 설정 누락 503 (테스트)
- [x] Firestore `data` 컬렉션에 146개 적재, summary가 마일스톤 1 기준값과 일치
- [x] 테스트 전부 통과 (네트워크 없이): **47 passed**
- [x] 키/비밀값 커밋 없음 (아직 커밋 전. `.env`와 키 JSON은 ignore 확인됨)

## Result (2026-09-25 실행)
- 적재: 1회차 `added 146`, 2회차 `added 0, skipped 146` (여러 번 실행해도 안전)
- 실제 Firestore로 확인한 흐름:
  - 생성 201 → 같은 날짜 재생성 409 → 음수 value 422
  - summary count 147 (latest가 새 값으로 바뀜)
  - 수정 200 → 다른 날짜와 겹치게 수정 409
  - 삭제 200 → 다시 삭제 404 → summary 146 (마일스톤 1 기준값과 동일)
- CORS: 허용 origin(`http://localhost:5500`) preflight에 `access-control-allow-origin` 헤더 응답
- 계획과 다른 점:
  - 의존성 조립을 `app/dependencies.py`로 분리했다 (마일스톤 3 대화 API에서 재사용)
  - `/`에 접속하면 `/docs`로 이동한다
  - `.claude/launch.json`(로컬 서버 실행 설정)을 추가했다
- 참고: Windows Git Bash에서 `curl -d`로 한글을 보내면 인자가 CP949로 바뀌어 400이 난다. 서버 문제가 아니며, UTF-8로 보내면 정상이다. Swagger UI나 프론트엔드에서는 발생하지 않는다.
