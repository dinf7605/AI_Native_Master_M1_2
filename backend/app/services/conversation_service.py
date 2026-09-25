"""대화 기록의 비즈니스 규칙. 제목 자동 생성과 존재 확인을 담당한다."""

from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from typing import Any

from app.errors import NotFoundError
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.conversation import ChatMessage, ConversationCreate

TITLE_LENGTH = 30


def make_title(messages: Sequence[ChatMessage]) -> str:
    """첫 user 메시지(없으면 첫 메시지)의 공백을 정리해 앞 TITLE_LENGTH자를 제목으로 쓴다."""
    source = next((m for m in messages if m.role == "user"), messages[0])
    text = " ".join(source.content.split())
    return text if len(text) <= TITLE_LENGTH else text[:TITLE_LENGTH] + "…"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConversationService:
    def __init__(
        self, repository: ConversationRepository, now: Callable[[], datetime] = utc_now
    ) -> None:
        self._repo = repository
        self._now = now

    def list_conversations(self) -> list[dict[str, Any]]:
        return self._repo.list_summaries()

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        conversation = self._repo.get(conversation_id)
        if conversation is None:
            raise NotFoundError(f"ID '{conversation_id}'에 해당하는 대화가 없습니다.")
        return conversation

    def create_conversation(self, payload: ConversationCreate) -> dict[str, Any]:
        messages = [message.model_dump() for message in payload.messages]
        now = self._now()
        return self._repo.create(
            {
                "title": payload.title or make_title(payload.messages),
                "messages": messages,
                "message_count": len(messages),
                "created_at": now,
                "updated_at": now,
            }
        )

    def delete_conversation(self, conversation_id: str) -> None:
        self.get_conversation(conversation_id)
        self._repo.delete(conversation_id)
