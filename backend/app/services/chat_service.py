"""AI 채팅 흐름 (컨텍스트 주입).

1) 데이터 요약 조회 → 2) 요약을 시스템 프롬프트에 삽입 → 3) GPT 호출 → 4) 대화 자동 저장

GPT 호출이 실패하면 아무것도 저장하지 않는다(질문만 남는 반쪽 대화 방지).
"""

from typing import Any

from app.llm import LLMClient
from app.prompts import build_system_prompt
from app.schemas.chat import ChatRequest
from app.schemas.conversation import MAX_CONTENT_LENGTH, ConversationCreate
from app.services.conversation_service import ConversationService
from app.services.data_service import DataService

HISTORY_LIMIT = 10  # 이어 쓰기 시 GPT에 함께 보내는 최근 메시지 수 (토큰 비용 상한)


class ChatService:
    def __init__(
        self,
        data_service: DataService,
        conversation_service: ConversationService,
        llm: LLMClient,
    ) -> None:
        self._data = data_service
        self._conversations = conversation_service
        self._llm = llm

    def chat(self, request: ChatRequest) -> dict[str, Any]:
        conversation = None
        if request.conversation_id:
            conversation = self._conversations.get_conversation(request.conversation_id)
            self._conversations.ensure_capacity(conversation, additional=2)

        summary = self._data.get_summary()
        history = conversation["messages"][-HISTORY_LIMIT:] if conversation else []
        llm_messages = [
            {"role": "system", "content": build_system_prompt(summary)},
            *({"role": m["role"], "content": m["content"]} for m in history),
            {"role": "user", "content": request.message},
        ]
        reply = self._llm.complete(llm_messages)[:MAX_CONTENT_LENGTH]

        new_messages = [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": reply},
        ]
        if conversation:
            saved = self._conversations.append_messages(conversation, new_messages)
        else:
            saved = self._conversations.create_conversation(ConversationCreate(messages=new_messages))

        return {
            "conversation_id": saved["id"],
            "title": saved["title"],
            "reply": reply,
            "model": self._llm.model,
            "summary": summary,
        }
