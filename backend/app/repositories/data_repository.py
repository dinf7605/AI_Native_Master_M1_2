"""Firestore `data` 컬렉션 접근. 비즈니스 규칙 없이 저장/조회만 담당한다.

문서 형태: data/{자동ID} = {date: "YYYY-MM-DD", value: float, memo: str, created_at, updated_at}
date를 ISO 문자열로 저장하므로 문자열 정렬이 곧 날짜순 정렬이다.
"""

from typing import Any, Protocol

from google.cloud.firestore import SERVER_TIMESTAMP, FieldFilter

COLLECTION = "data"
BATCH_LIMIT = 500


class DataRepository(Protocol):
    def list_all(self) -> list[dict[str, Any]]: ...
    def get(self, item_id: str) -> dict[str, Any] | None: ...
    def find_by_date(self, day: str) -> list[dict[str, Any]]: ...
    def create(self, fields: dict[str, Any]) -> dict[str, Any]: ...
    def create_many(self, rows: list[dict[str, Any]]) -> int: ...
    def update(self, item_id: str, fields: dict[str, Any]) -> dict[str, Any]: ...
    def delete(self, item_id: str) -> None: ...


class FirestoreDataRepository:
    def __init__(self, client) -> None:
        self._client = client
        self._collection = client.collection(COLLECTION)

    def list_all(self) -> list[dict[str, Any]]:
        return [_to_record(snap) for snap in self._collection.order_by("date").stream()]

    def get(self, item_id: str) -> dict[str, Any] | None:
        snap = self._collection.document(item_id).get()
        return _to_record(snap) if snap.exists else None

    def find_by_date(self, day: str) -> list[dict[str, Any]]:
        query = self._collection.where(filter=FieldFilter("date", "==", day))
        return [_to_record(snap) for snap in query.stream()]

    def create(self, fields: dict[str, Any]) -> dict[str, Any]:
        ref = self._collection.document()
        ref.set({**fields, "created_at": SERVER_TIMESTAMP, "updated_at": SERVER_TIMESTAMP})
        return {"id": ref.id, **fields}

    def create_many(self, rows: list[dict[str, Any]]) -> int:
        for start in range(0, len(rows), BATCH_LIMIT):
            batch = self._client.batch()
            for fields in rows[start : start + BATCH_LIMIT]:
                batch.set(
                    self._collection.document(),
                    {**fields, "created_at": SERVER_TIMESTAMP, "updated_at": SERVER_TIMESTAMP},
                )
            batch.commit()
        return len(rows)

    def update(self, item_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        self._collection.document(item_id).update({**fields, "updated_at": SERVER_TIMESTAMP})
        return {"id": item_id, **fields}

    def delete(self, item_id: str) -> None:
        self._collection.document(item_id).delete()


def _to_record(snap) -> dict[str, Any]:
    data = snap.to_dict()
    return {"id": snap.id, "date": data["date"], "value": data["value"], "memo": data.get("memo", "")}
