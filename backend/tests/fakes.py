"""테스트용 인메모리 repository. FirestoreDataRepository와 같은 메서드를 제공한다."""

from typing import Any


class InMemoryDataRepository:
    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._next_id = 1

    def list_all(self) -> list[dict[str, Any]]:
        return sorted((dict(item) for item in self._items.values()), key=lambda r: r["date"])

    def get(self, item_id: str) -> dict[str, Any] | None:
        item = self._items.get(item_id)
        return dict(item) if item else None

    def find_by_date(self, day: str) -> list[dict[str, Any]]:
        return [dict(item) for item in self._items.values() if item["date"] == day]

    def create(self, fields: dict[str, Any]) -> dict[str, Any]:
        item_id = f"id{self._next_id}"
        self._next_id += 1
        self._items[item_id] = {"id": item_id, **fields}
        return dict(self._items[item_id])

    def create_many(self, rows: list[dict[str, Any]]) -> int:
        for fields in rows:
            self.create(fields)
        return len(rows)

    def update(self, item_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        self._items[item_id] = {"id": item_id, **fields}
        return dict(self._items[item_id])

    def delete(self, item_id: str) -> None:
        self._items.pop(item_id, None)
