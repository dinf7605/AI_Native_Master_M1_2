"""`/api/conversations` 요청/응답 모델. 요청 검증 규칙은 모두 여기에서 선언한다."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# 최악의 경우 50개 × 4000자 × 3바이트(한글) ≈ 600KB로 Firestore 문서 한도(1MB) 안에 든다.
MAX_MESSAGES = 50
MAX_CONTENT_LENGTH = 4000
MAX_TITLE_LENGTH = 100


class ChatMessage(BaseModel):
    """대화 메시지. system 역할은 서버만 만들 수 있으므로 클라이언트 입력으로 받지 않는다."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_CONTENT_LENGTH)


class ConversationCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "환율 추세 질문",
                    "messages": [
                        {"role": "user", "content": "최근 환율 추세가 어때?"},
                        {"role": "assistant", "content": "최근 7영업일 평균이 1.94% 올랐습니다."},
                    ],
                }
            ]
        },
    )

    title: str | None = Field(
        default=None, max_length=MAX_TITLE_LENGTH, description="비우면 첫 질문으로 자동 생성한다."
    )
    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_MESSAGES)


class ConversationSummary(BaseModel):
    """목록용. messages는 포함하지 않는다."""

    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[ChatMessage]
