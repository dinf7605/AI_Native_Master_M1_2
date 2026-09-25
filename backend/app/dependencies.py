"""FastAPI 의존성 조립. 테스트에서는 get_data_repository를 가짜 repository로 교체한다."""

from fastapi import Depends

from app.firebase import get_firestore_client
from app.repositories.data_repository import DataRepository, FirestoreDataRepository
from app.services.data_service import DataService


def get_data_repository() -> DataRepository:
    return FirestoreDataRepository(get_firestore_client())


def get_data_service(repository: DataRepository = Depends(get_data_repository)) -> DataService:
    return DataService(repository)
