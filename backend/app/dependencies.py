"""FastAPI 의존성 조립. 테스트에서는 get_*_repository를 가짜 repository로 교체한다."""

from fastapi import Depends

from app.firebase import get_firestore_client
from app.repositories.conversation_repository import (
    ConversationRepository,
    FirestoreConversationRepository,
)
from app.repositories.data_repository import DataRepository, FirestoreDataRepository
from app.services.conversation_service import ConversationService
from app.services.data_service import DataService


def get_data_repository() -> DataRepository:
    return FirestoreDataRepository(get_firestore_client())


def get_data_service(repository: DataRepository = Depends(get_data_repository)) -> DataService:
    return DataService(repository)


def get_conversation_repository() -> ConversationRepository:
    return FirestoreConversationRepository(get_firestore_client())


def get_conversation_service(
    repository: ConversationRepository = Depends(get_conversation_repository),
) -> ConversationService:
    return ConversationService(repository)
