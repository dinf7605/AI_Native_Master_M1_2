"""`/api/chat` 엔드포인트. HTTP 입출력만 담당하고 흐름은 ChatService에 위임한다."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_chat_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])

Service = Annotated[ChatService, Depends(get_chat_service)]


@router.post(
    "",
    response_model=ChatResponse,
    summary="AI 채팅 (데이터 요약 주입)",
    description="1) 데이터 요약 조회 → 2) 요약을 시스템 프롬프트에 삽입 → 3) GPT 호출 → "
    "4) 대화를 conversations에 자동 저장. conversation_id를 보내면 그 대화의 최근 10개 메시지를 "
    "맥락으로 이어서 답한다. GPT 호출 실패 시 502(저장하지 않음), 대화 메시지 한도 초과 시 409.",
)
def chat(payload: ChatRequest, service: Service):
    return service.chat(payload)
