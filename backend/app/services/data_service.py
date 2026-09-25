"""데이터 CRUD의 비즈니스 규칙. HTTP나 Firestore 세부사항을 모르고 repository에만 의존한다.

규칙: 날짜당 1건만 허용한다(중복 시 DuplicateDateError), 없는 ID는 NotFoundError.
"""

from typing import Any

from app.errors import DuplicateDateError, NotFoundError
from app.repositories.data_repository import DataRepository
from app.schemas.data import DataCreate
from app.services.analysis import build_summary


def to_fields(payload: DataCreate) -> dict[str, Any]:
    """검증된 요청을 저장용 필드로 변환한다 (date는 ISO 문자열)."""
    return {"date": payload.date.isoformat(), "value": payload.value, "memo": payload.memo}


class DataService:
    def __init__(self, repository: DataRepository) -> None:
        self._repo = repository

    def list_items(self) -> list[dict[str, Any]]:
        return self._repo.list_all()

    def create_item(self, payload: DataCreate) -> dict[str, Any]:
        fields = to_fields(payload)
        self._ensure_date_available(fields["date"])
        return self._repo.create(fields)

    def update_item(self, item_id: str, payload: DataCreate) -> dict[str, Any]:
        self._ensure_exists(item_id)
        fields = to_fields(payload)
        self._ensure_date_available(fields["date"], exclude_id=item_id)
        return self._repo.update(item_id, fields)

    def delete_item(self, item_id: str) -> None:
        self._ensure_exists(item_id)
        self._repo.delete(item_id)

    def get_summary(self) -> dict[str, Any]:
        return build_summary(self._repo.list_all())

    def _ensure_exists(self, item_id: str) -> None:
        if self._repo.get(item_id) is None:
            raise NotFoundError(f"ID '{item_id}'에 해당하는 데이터가 없습니다.")

    def _ensure_date_available(self, day: str, exclude_id: str | None = None) -> None:
        if any(item["id"] != exclude_id for item in self._repo.find_by_date(day)):
            raise DuplicateDateError(f"{day} 날짜의 데이터가 이미 있습니다. 수정 기능을 사용하세요.")
