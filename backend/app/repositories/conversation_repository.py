"""Firestore `conversations` 컬렉션 접근. 비즈니스 규칙 없이 저장/조회만 담당한다.

문서 형태: conversations/{자동ID} =
    {title, messages: [{role, content}], message_count, created_at, updated_at}
"""

from typing import Any, Protocol

from google.cloud.firestore import Query

COLLECTION = "conversations"
SUMMARY_FIELDS = ["title", "message_count", "created_at", "updated_at"]


class ConversationRepository(Protocol):
    def list_summaries(self) -> list[dict[str, Any]]: ...
    def get(self, conversation_id: str) -> dict[str, Any] | None: ...
    def create(self, fields: dict[str, Any]) -> dict[str, Any]: ...
    def delete(self, conversation_id: str) -> None: ...


class FirestoreConversationRepository:
    def __init__(self, client) -> None:
        self._collection = client.collection(COLLECTION)

    def list_summaries(self) -> list[dict[str, Any]]:
        # select()로 messages 필드는 읽지 않는다. 대화가 길어져도 목록 응답은 가볍다.
        query = self._collection.select(SUMMARY_FIELDS).order_by(
            "updated_at", direction=Query.DESCENDING
        )
        return [{"id": snap.id, **snap.to_dict()} for snap in query.stream()]

    def get(self, conversation_id: str) -> dict[str, Any] | None:
        snap = self._collection.document(conversation_id).get()
        return {"id": snap.id, **snap.to_dict()} if snap.exists else None

    def create(self, fields: dict[str, Any]) -> dict[str, Any]:
        ref = self._collection.document()
        ref.set(fields)
        return {"id": ref.id, **fields}

    def delete(self, conversation_id: str) -> None:
        self._collection.document(conversation_id).delete()
