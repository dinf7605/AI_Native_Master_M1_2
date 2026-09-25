# Plan: 대화 기록 API (Firestore)

**Source PRD**: `.claude/prds/fx-data-ai-chat.prd.md`
**Selected Milestone**: #3 대화 기록 API
**Complexity**: Small

## Summary
Firestore `conversations` 컬렉션에 대화를 저장하고, 목록 조회·단건 조회·삭제를 제공한다. "대화 불러오기"는 PRD에서 확정한 옵션 (A)를 따른다. 목록은 메타데이터만 반환하고, `GET /api/conversations/{id}`가 전체 messages를 반환한다. 마일스톤 2의 router → service → repository 구조와 테스트 방식을 그대로 따른다.

## Decisions
| 질문 | 결정 | 근거 |
|---|---|---|
| 문서 형태 | `conversations/{자동ID}` = `{title, messages: [{role, content}], message_count, created_at, updated_at}` | 대화 1건 = 문서 1개. 불러오기는 읽기 1회로 끝남 |
| 목록 응답 | `id, title, message_count, created_at, updated_at`만 반환. `updated_at` 내림차순(최근 대화 먼저). Firestore `select()`로 messages 필드를 아예 읽지 않음 | 옵션 (A). 대화가 늘어도 목록 응답이 가벼움 |
| 허용 role | `user`, `assistant`만 허용. `system`은 422 | 시스템 프롬프트는 서버가 만든다. 클라이언트가 저장된 대화에 system 메시지를 끼워 넣는 것(프롬프트 주입)을 차단 |
| 입력 제한 | messages 1~50개, content 1~4000자(공백 제거 후), title 최대 100자, 정의되지 않은 필드는 거부 | 최악의 경우 50 × 4000자 × 3바이트(한글) ≈ 600KB로 Firestore 문서 한도 1MB 안. 이후 GPT 토큰 비용도 보호 |
| 제목 | 요청에 title이 없거나 공백이면, 첫 user 메시지의 앞 30자로 자동 생성 (넘치면 `…`) | 목록 화면에서 대화를 구분하기 쉬움 |
| 시각 | 서비스에서 `datetime.now(UTC)`로 넣음 (SERVER_TIMESTAMP 아님) | 생성 응답에 실제 시각을 바로 담기 위해 |
| 공통 요소 | `MessageResponse`와 문서 ID 경로 검증을 `schemas/common.py`로 옮겨 data/conversations가 공유 | 중복 제거 |
| 이어 쓰기(메시지 추가) | 이번 범위 밖. 마일스톤 4 채팅 API에서 필요한 메서드를 추가 | 범위 분리 |

## Patterns to Mirror
| Category | Source | Pattern |
|---|---|---|
| 계층 | `backend/app/routers/data.py`, `services/data_service.py`, `repositories/data_repository.py` | router는 HTTP만, service는 규칙(NotFoundError), repository는 Firestore만 |
| 의존성 | `backend/app/dependencies.py:10` | `get_*_repository`를 테스트에서 `dependency_overrides`로 fake 교체 |
| 테스트 | `backend/tests/test_data_api.py:15`, `tests/fakes.py` | TestClient fixture + InMemory fake |
| 에러 | `backend/app/errors.py` | 도메인 예외 → `main.py` 핸들러가 상태코드 매핑 |

## Files to Change
| File | Action | Why |
|---|---|---|
| `backend/app/schemas/common.py` | CREATE | `MessageResponse`, `DocumentId` 공유 |
| `backend/app/schemas/data.py`, `routers/data.py` | UPDATE | 공통 요소를 common에서 import |
| `backend/app/schemas/conversation.py` | CREATE | 요청/응답 모델 + 검증 |
| `backend/app/repositories/conversation_repository.py` | CREATE | Firestore 접근 |
| `backend/app/services/conversation_service.py` | CREATE | 제목 생성, 존재 확인 |
| `backend/app/routers/conversations.py` | CREATE | 엔드포인트 4개 |
| `backend/app/dependencies.py`, `backend/main.py` | UPDATE | 의존성·라우터 등록 |
| `backend/tests/fakes.py` | UPDATE | `InMemoryConversationRepository` |
| `backend/tests/test_conversations_api.py` | CREATE | API/검증/제목 테스트 |

## Tasks
1. **테스트 먼저 (RED)**:
   - 생성 201과 제목 자동 생성, 명시적 제목 유지
   - 422: system role, 빈 messages, 빈/초과 content, messages 51개, 알 수 없는 필드
   - 목록에 messages가 없고 최신순
   - 단건 조회 전체 messages / 404
   - 삭제 200 → 조회 404 / 없는 id 404
   - 잘못된 id 형식 422
2. **공통 스키마 분리 + conversation 스키마**
3. **repository / service / router / 의존성 등록 (GREEN)**
4. **실제 Firestore 확인**: 서버를 띄운다. 생성 → 목록 → 단건 → 삭제를 한 바퀴 돈 뒤, 테스트 대화를 정리한다.

## Validation
```bash
cd backend
.venv/Scripts/python -m pytest -q
# 서버 실행 후 UTF-8로 POST/GET/DELETE /api/conversations 확인 (Python urllib 사용 — Windows curl 한글 인코딩 문제 회피)
```

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| 대화가 길어져 문서 1MB 초과 | Low | messages 50개 × content 4000자 상한 (최악 약 600KB). 마일스톤 4 채팅 API도 같은 상한을 따른다 |
| `updated_at` 정렬 필드가 없는 문서는 목록에서 빠짐 | Low | 모든 문서를 서비스가 만들기 때문에 항상 존재 |
| Windows 시계 해상도로 같은 시각 → 정렬 불안정 | Low | 정렬 테스트는 fake에 시각을 명시해 검증 |

## Acceptance
- [x] `/docs`에 conversations 엔드포인트 4개가 설명과 함께 보인다
- [x] 목록은 가볍게(메타데이터만), 단건 조회는 전체 messages
- [x] system role·빈 메시지·초과 길이·51개 메시지는 422, 없는 id는 404
- [x] 실제 Firestore에서 저장 → 목록 → 불러오기 → 삭제가 동작
- [x] 전체 테스트 통과: **66 passed** (신규 19)

## Result (2026-09-25 실행)
실제 Firestore에서 확인한 흐름:
- 생성 201: 제목 자동 생성 "최근 환율 추세가 어때?", 명시한 제목도 유지
- system role 422
- 목록: 최신순이고 `messages` 키가 없음
- 불러오기: 전체 messages가 원본과 같음
- 삭제 200 → 다시 조회 404 → 목록이 비었음 (테스트 데이터 정리 완료)

`select()` + `order_by("updated_at")` 조합은 복합 색인 없이 동작했다.
