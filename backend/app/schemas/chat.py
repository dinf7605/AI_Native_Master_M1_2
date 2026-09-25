"""`/api/chat` 요청/응답 모델."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import DOCUMENT_ID_PATTERN
from app.schemas.data import SummaryResponse

MAX_QUESTION_LENGTH = 1000


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={"examples": [{"message": "최근 환율 추세가 어때?"}]},
    )

    message: str = Field(
        min_length=1, max_length=MAX_QUESTION_LENGTH, description="사용자 질문 (최대 1000자)"
    )
    conversation_id: str | None = Field(
        default=None,
        pattern=DOCUMENT_ID_PATTERN,
        description="이어서 대화할 대화 ID. 비우면 새 대화를 만든다.",
    )


class ChatResponse(BaseModel):
    conversation_id: str
    title: str
    reply: str
    model: str
    summary: SummaryResponse = Field(description="이번 답변의 시스템 프롬프트에 주입된 데이터 요약")
