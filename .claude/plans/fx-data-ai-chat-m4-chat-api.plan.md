# Plan: 컨텍스트 주입 AI 채팅 API

**Source PRD**: `.claude/prds/fx-data-ai-chat.prd.md`
**Selected Milestone**: #4 컨텍스트 주입 AI 채팅 API
**Complexity**: Medium

## Summary
`POST /api/chat`을 구현한다. 흐름은 다음과 같다.
1. 데이터 요약을 계산한다.
2. 요약을 한국어 시스템 프롬프트에 넣는다.
3. 코디세이 게이트웨이(OpenAI 호환)로 GPT를 호출한다.
4. 질문과 답변을 `conversations`에 자동 저장한다.

`conversation_id`를 보내면 해당 대화의 최근 메시지를 맥락으로 이어서 답한다. 비용을 보호하기 위해 답변 길이, 질문 길이, 이력 개수에 상한을 둔다.

## Decisions
| 질문 | 결정 | 근거 |
|---|---|---|
| API 주소 | `OPENAI_BASE_URL=https://copa.codyssey.kr/v1` (`/v1` 없으면 401, 실제 확인) | 코디세이 교육용 OpenAI 호환 게이트웨이 |
| 모델 | 기본 `gpt-5.4`, `OPENAI_MODEL`로 교체 가능 (`gpt-5.5`는 차감 2배) | 짧은 데이터 서술 답변에는 5.4로 충분. 비용 절반 |
| 파라미터 | `max_completion_tokens`만 사용 (기본 700, `OPENAI_MAX_COMPLETION_TOKENS`). `reasoning_effort`는 게이트웨이가 거부(400 unsupported_feature)하므로 쓰지 않음 | 실제 호출로 확인: 25토큰, 2초 응답 |
| 요약 조회 방식 | 라우터가 자기 자신에게 HTTP 요청하지 않고 `/api/data/summary`와 같은 `DataService.get_summary()`를 직접 호출 | 같은 계산을 재사용하며 네트워크 왕복·콜드스타트 영향 없음 |
| 시스템 프롬프트 | 요약을 사람이 읽는 한국어 목록으로 변환해 넣고, 규칙을 명시: 요약 밖 수치 추측 금지, 투자 조언 금지, 단기 추세라는 한계 명시, 5문장 이내, 지시문 변경 요청 거부 | PRD 성공지표(요약 수치 5/5 일치)와 투자 조언 리스크 대응 |
| 입력 제한 | `message` 1~1000자, `conversation_id` 문서 ID 형식, 알 수 없는 필드는 거부 | 토큰 비용 보호 |
| 이어 쓰기 | `conversation_id`가 있으면 해당 대화의 **최근 10개** 메시지를 GPT에 함께 보내고, 새 질문과 답변을 그 대화에 추가한다. 없으면 새 대화를 만든다 | PRD Open Question 해소 |
| 한도 | 대화가 50개 메시지 한도를 넘게 되면 409 ("새 대화를 시작하세요"). GPT는 호출하지 않는다 | 마일스톤 3의 Firestore 문서 크기 상한 유지 |
| 실패 시 | GPT 호출이 실패하면 502, 아무것도 저장하지 않는다. 키가 없으면 503 | 반쪽 대화(질문만 저장) 방지 |
| 응답 | `{conversation_id, title, reply, model, summary}`. summary는 주입된 요약 원본 | 프론트가 "이 요약을 근거로 답했다"를 보여줄 수 있음 |

## Patterns to Mirror
| Category | Source | Pattern |
|---|---|---|
| 계층 | `routers/conversations.py`, `services/conversation_service.py` | router는 HTTP만, 서비스가 규칙. ChatService는 DataService·ConversationService·LLM을 조합 |
| 외부 연동 | `app/firebase.py`, `app/config.py` | 설정은 config에서만 읽고, 누락 시 도메인 예외(503) |
| 테스트 | `tests/test_conversations_api.py`, `tests/fakes.py` | dependency_overrides로 repository와 LLM을 fake로 교체. 실제 GPT 호출 없음 |

## Files to Change
| File | Action | Why |
|---|---|---|
| `backend/.env.example` | UPDATE | `OPENAI_BASE_URL`, `OPENAI_MODEL` (완료) |
| `backend/app/config.py` | UPDATE | `get_openai_settings()` |
| `backend/app/errors.py` | UPDATE | `LLMUnavailableError`(503), `LLMRequestError`(502), `ConversationLimitError`(409) |
| `backend/app/llm.py` | CREATE | `OpenAIChatClient` (게이트웨이 호출, 오류 변환) |
| `backend/app/prompts.py` | CREATE | `build_system_prompt(summary)` 순수 함수 |
| `backend/app/schemas/common.py` | UPDATE | 문서 ID 정규식 상수 공유 |
| `backend/app/schemas/chat.py` | CREATE | `ChatRequest`, `ChatResponse` |
| `backend/app/repositories/conversation_repository.py` | UPDATE | `update()` 추가 |
| `backend/app/services/conversation_service.py` | UPDATE | `ensure_capacity()`, `append_messages()` |
| `backend/app/services/chat_service.py` | CREATE | 채팅 흐름 |
| `backend/app/routers/chat.py` | CREATE | `POST /api/chat` |
| `backend/app/dependencies.py`, `backend/main.py` | UPDATE | 의존성·라우터 등록 |
| `backend/tests/fakes.py` | UPDATE | `FakeLLMClient`, 대화 fake에 `update` |
| `backend/tests/test_prompts.py`, `test_chat_api.py`, `test_config.py` | CREATE/UPDATE | 테스트 |

## Tasks
1. **테스트 먼저 (RED)**
   - 프롬프트: 요약 수치와 규칙 포함, 빈 데이터 처리
   - 설정: 키 누락 시 503 예외, 기본값, 잘못된 정수
   - 채팅:
     - 새 대화 생성과 저장 (메시지 2개, 제목 = 질문)
     - LLM이 받은 system 메시지에 요약 수치가 들어 있음
     - 이어 쓰기 시 이력 전달, 이력은 최근 10개로 제한
     - 없는 대화 404, 한도 초과 409 (둘 다 LLM 미호출)
     - 입력 422
     - LLM 실패 502 이후 저장 없음
2. **config / errors / prompts / llm**
3. **conversation 확장 + ChatService + router (GREEN)**
4. **실제 게이트웨이로 확인**:
   - 질문 5개를 보내 답변을 요약 수치와 대조한다 (PRD 성공지표)
   - 이어 쓰기 1회, 투자 조언 요청 1회를 확인한다
   - 확인이 끝나면 대화를 정리한다
   - 호출 수를 최소로 해서 크레딧 사용을 줄인다

## Validation
```bash
cd backend
.venv/Scripts/python -m pytest -q
# 서버 실행 후 UTF-8로 POST /api/chat → 답변과 /api/data/summary 대조
```

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| 공개 배포 후 `/api/chat` 남용으로 크레딧 소진 | Med | 이번엔 길이·이력 상한만 둔다. 요청 빈도 제한과 CORS는 배포 마일스톤(7)에서 보강 |
| 게이트웨이가 일부 파라미터·기능 미지원 | Med | 확인된 파라미터(`max_completion_tokens`)만 사용 |
| AI가 요약에 없는 수치를 지어냄 | Med | 프롬프트 규칙과 실제 질문 5개 대조로 검증 |
| GPT 응답 지연(수 초) + Render 콜드스타트 | Med | 서버 타임아웃 60초, 재시도 1회. 로딩 표시는 마일스톤 5 |
| 답변이 4000자 저장 한도 초과 | Low | 700토큰 상한이면 도달 불가. 방어적으로 저장 전 4000자로 자름 |

## Acceptance
- [x] `/docs`에 `POST /api/chat`과 흐름 설명이 보인다
- [x] 답변이 요약 수치와 일치 (실제 질문 **5/5**)
- [x] 대화가 자동 저장되고, `conversation_id`로 이어서 대화할 수 있다
- [x] 404/409/422/502/503 오류 처리 (테스트)
- [x] 전체 테스트 통과 (실제 GPT 호출 없이): **90 passed** (신규 24)

## Result (2026-09-25, gpt-5.4, 코디세이 게이트웨이)
| 질문 | 답변 핵심 | 응답 시간 |
|---|---|---|
| 기간과 개수 | 2026-03-02 ~ 2026-09-24, 146개 | 2.4s |
| 평균 | 1,466.60원 | 1.2s |
| 최고 | 1,558.09원 (2026-07-01) | 1.1s |
| 최저 | 1,336.20원 (2026-09-09) | 1.1s |
| 최근 추세 | 증가, 최근 7개 평균이 직전보다 1.94% 높음, "단기 비교 기준"이라고 명시 | 1.7s |
| 이어 쓰기: 최신값 vs 평균 | 1,368.60원 < 1,466.60원 (98.00원 낮음). 같은 대화에 저장되어 message_count 4 | 1.3s |
| 투자 조언 요청 ("사라고 해줘") | 추천을 거절하고 데이터 사실만 설명 | 2.7s |

- 실제 호출은 모두 7회였다. 테스트 대화는 삭제했다.
- 계획 대비 추가: `OpenAISettings.api_key`는 `repr=False`로 두어 로그나 디버그 출력에 키가 찍히지 않게 했다.
