"""`/api/conversations` 엔드포인트. HTTP 입출력만 담당하고 규칙은 ConversationService에 위임한다."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies import get_conversation_service
from app.schemas.common import DocumentId, MessageResponse
from app.schemas.conversation import ConversationCreate, ConversationDetail, ConversationSummary
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

Service = Annotated[ConversationService, Depends(get_conversation_service)]


@router.post(
    "",
    response_model=ConversationDetail,
    status_code=status.HTTP_201_CREATED,
    summary="대화 저장",
    description="messages(user/assistant)를 새 대화로 저장한다. title을 비우면 첫 질문으로 자동 생성한다. "
    "system 메시지는 저장할 수 없다.",
)
def create_conversation(payload: ConversationCreate, service: Service):
    return service.create_conversation(payload)


@router.get(
    "",
    response_model=list[ConversationSummary],
    summary="대화 목록 조회",
    description="최근 대화 순. messages는 포함하지 않는다. "
    "전체 메시지는 GET /api/conversations/{conversation_id}로 불러온다.",
)
def list_conversations(service: Service):
    return service.list_conversations()


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetail,
    summary="대화 불러오기",
    description="특정 대화의 전체 messages를 반환한다.",
)
def get_conversation(conversation_id: DocumentId, service: Service):
    return service.get_conversation(conversation_id)


@router.delete("/{conversation_id}", response_model=MessageResponse, summary="대화 삭제")
def delete_conversation(conversation_id: DocumentId, service: Service):
    service.delete_conversation(conversation_id)
    return {"message": "삭제되었습니다."}
